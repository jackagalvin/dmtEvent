import time
from threading import Thread

import numpy as np
from scipy import signal, interpolate
from pylsl import StreamInlet, resolve_byprop
from liblo import ServerThread, Address, Message, Bundle, send

import live_utils as ut

port = 4321
oscip = "127.0.0.1"
#oscip = "192.168.1.31"
oscport = 8001

class FFTServer():
    def __init__(self, incoming, outgoing,  sparseOutput=None, config={}, device_source='Muse',software_source='muselsl', debug_outputs=True, verbose=False):
        self.incoming = incoming
        self.outgoing = outgoing
        self.eeg_chunk_length = 12
        self.threshold = 30
        self.conc_level = 50
        self.inc = 2

        self._osc_server = ServerThread(incoming['port'])
        print('OSC server initialized at port {}.'.format(incoming['port']))

        if not isinstance(self.outgoing, tuple):
            self.outgoing = [self.outgoing]
        self._output_threads = []
        for out in self.outgoing:
            self._output_threads.append(Address(out['address'],out['port']))
        print('OSC client initialized at {}:{}.'.format(
                            out['address'], out['port']))

        self._init_processing(config)

        self.incremented_value = 50;

    def _init_processing(self, config):
        DEFAULT_CONFIG = {'fs': 256.,
                          'n_channels': 5,
                          'raw_buffer_len': 3 * 256,
                          'filt_buffer_len': 3 * 256,
                          'window_len': 256,
                          'step': int(256 / 10),
                          'filter': ([1], [1]),
                          'filter_bank': {},
                          'psd_window_len': 256.,
                          'psd_buffer_len': 10}
        config = {**DEFAULT_CONFIG, **config}

        self.fs = config['fs']
        self.n_channels = config['n_channels']
        self.eeg_ch_remap = None
        self.n_channels = 4

        raw_buffer_len = int(config['raw_buffer_len'])
        filt_buffer_len = int(config['filt_buffer_len'])


        self.eeg_buffer = ut.NanBuffer(raw_buffer_len, self.n_channels)
        self.filt_eeg_buffer = ut.CircularBuffer(filt_buffer_len,self.n_channels)
        self.hpfilt_eeg_buffer = ut.CircularBuffer(filt_buffer_len,self.n_channels)
        self.smooth_eeg_buffer = ut.CircularBuffer(filt_buffer_len,self.n_channels)

        if config['filter']:
            if isinstance(config['filter'], tuple):
                b = config['filter'][0]
                a = config['filter'][1]
            elif isinstance(config['filter'], dict):
                b, a = ut.get_filter_coeff(self.fs, **config['filter'])
            zi = np.tile(signal.lfilter_zi(b, a), (self.n_channels, 1)).T
            self.bandpass_filt = {'b': b,'a': a,'zi': zi}

        if config['hpfilter']:
            b = config['hpfilter'][0]
            a = config['hpfilter'][1]
            zi = np.tile(signal.lfilter_zi(b, a), (self.n_channels, 1)).T
            self.hp_filt = {'b': b,'a': a,'zi': zi}

        if config['lpfilter']:
            b = config['lpfilter'][0]
            a = config['lpfilter'][1]
            zi = np.tile(signal.lfilter_zi(b, a), (self.n_channels, 1)).T
            self.lp_filt = {'b': b,'a': a,'zi': zi}

        if config['filter_bank']:
            self.filter_bank = {}
            for name, coeff in config['filter_bank'].items():
                zi = np.tile(signal.lfilter_zi(coeff[0], coeff[1]),(self.n_channels, 1)).T
                self.filter_bank[name] = {'b': coeff[0],'a': coeff[1],'zi': zi}


        self.window_len = int(config['window_len'])
        self.step = int(config['step'])

        psd_buffer_len = int(config['psd_buffer_len'])
        self.psd_buffer = ut.CircularBuffer(psd_buffer_len, 129,self.n_channels)

        decayRate = 0.997
        self.hists = {'delta': ut.Histogram(1000, self.n_channels, bounds=(0, 50), min_count=80, decay=decayRate ),
                      'theta': ut.Histogram(1000, self.n_channels, bounds=(0, 30),min_count=80, decay=decayRate),
                      'alpha': ut.Histogram(1000, self.n_channels,bounds=(0, 20), min_count=80, decay=decayRate),
                      'beta': ut.Histogram(1000, self.n_channels,bounds=(0, 10), min_count=80, decay=decayRate),
                      'gamma': ut.Histogram(1000, self.n_channels,bounds=(0, 10), min_count=80, decay=decayRate)
                      }

        self.firstWindowProc = True


    def _update_eeg_liblo_osc(self, path, args):
        sample = np.array(args).reshape(1, -1)
        self._process_eeg(sample[:, :self.n_channels], 0)


    def _process_eeg(self, samples, timestamp):
        self.eeg_buffer.update(samples)
        filt_samples = samples

        if config['filter']:
            filt_samples, self.bandpass_filt['zi'] = signal.lfilter(self.bandpass_filt['b'], self.bandpass_filt['a'],samples, axis=0, zi=self.bandpass_filt['zi'])
        self.filt_eeg_buffer.update(filt_samples)

        if config['hpfilter']:
            filt_samples, self.hp_filt['zi'] = signal.lfilter(self.hp_filt['b'], self.hp_filt['a'],filt_samples, axis=0, zi=self.hp_filt['zi'])
        self.hpfilt_eeg_buffer.update(filt_samples)

        if config['lpfilter']:
            smooth_eeg_samples, self.lp_filt['zi'] = signal.lfilter(self.lp_filt['b'], self.lp_filt['a'],filt_samples, axis=0, zi=self.lp_filt['zi'])
        else:
            smooth_eeg_samples = filt_samples
        self.smooth_eeg_buffer.update(smooth_eeg_samples)

        if config['filter_bank']:
            filter_bank_samples = {}
            for name, filt_dict in self.filter_bank.items():
                filter_bank_samples[name], self.filter_bank[name]['zi'] = signal.lfilter(filt_dict['b'], filt_dict['a'],filt_samples, axis=0,zi=self.filter_bank[name]['zi'])
            low_freq_chs = filter_bank_samples['delta'][0, [0, 2]] #+ filter_bank_samples['theta'][0, [0, 1]]

        window = self.smooth_eeg_buffer.extract(self.window_len)

        if self.smooth_eeg_buffer.pts%3==0:
            self._send_output_vec(smooth_eeg_samples, timestamp, 'muse/eeg')

        if self.eeg_buffer.pts > self.step:
            self.eeg_buffer.pts = 0

            if config['lpfilter']:
                window = self.smooth_eeg_buffer.extract(self.window_len)
            psd_raw_buffer = self.eeg_buffer.extract(self.window_len)
            psd, f = ut.fft_continuous(psd_raw_buffer, n=int(self.fs), psd=True,log='psd', fs=self.fs, window='hamming')
            self.psd_buffer.update(np.expand_dims(psd, axis=0))
            mean_psd = np.nanmean(self.psd_buffer.extract(), axis=0)

            bandPowers, bandNames = ut.compute_band_powers(mean_psd, f, relative=True)
            ratioPowers, ratioNames = ut.compute_band_ratios(bandPowers)

            if  (self.firstWindowProc):
                self.band_powers = bandPowers
                self.band_names = bandNames
                self.ratio_powers = ratioPowers
                self.ratio_names = ratioNames
                self.scores = np.zeros((len(self.band_names), self.n_channels))
                self.firstWindowProc = False


            for i, (name, hist) in enumerate(self.hists.items()):
                self.band_powers = bandPowers
                self.ratio_powers = ratioPowers

            self.combine_bands = ut.get_combined_bands(self.band_powers)
            self.concentration = ut.compute_concentration(ut.get_combined_bands(self.band_powers))

            if self.conc_level >= 0 and self.conc_level <=98:
                self.conc_level+=ut.concentration_incrementer(ut.compute_concentration(ut.get_combined_bands(self.band_powers)),self.threshold)



            band_names = ['delta','theta','alpha','beta','gamma']

            self._send_bands(self.combine_bands,timestamp,band_names)
            self._send_outputs(self.band_powers, timestamp, 'bands')
            self._send_outputs(self.ratio_powers, timestamp, 'ratios')
            self._send_float(self.concentration, timestamp, 'concentration')
            print(self.concentration)
            self._send_float(100-self.concentration, timestamp, 'arousal')
            self._send_float(self.conc_level,timestamp,'concentration_incremented')
            self._send_float(100 - self.conc_level, timestamp,'arousal_incremented')


    def inc_inc(self,num):
        self.incremented_value+=num

    def _send_outputs(self, output, timestamp, name):
        for out in self._output_threads:
            for c in range(self.n_channels):
                new_output = [('f', x) for x in output[:, c]]
                message = Message('/{}{}'.format(name, c), *new_output)
                send(out,  message)

    def _send_output_vec(self, output, timestamp, name):
        for out in self._output_threads:
            new_output = [('f', x) for x in output[0,:]]
            message = Message('/{}'.format(name), *new_output)
            send(out, message)

    def _send_output(self, output, timestamp, name):
        for out in self._output_threads:
            if (np.array(output).size==1):
                new_output = [('f', np.asscalar(output))]
                message = Message('/{}'.format(name), *new_output)
            send(out, message)

    def _send_float(self, output, timestamp, name):
        for out in self._output_threads:
            new_output = [('f', output)]
            message = Message('/{}'.format(name), *new_output)
            send(out, message)

    def _send_bands(self, output, timestamp, names):
        for out in self._output_threads:
            for i in range(5):
                new_output = [('f', output[i])]
                message = Message('/{}'.format(names[i]), *new_output)
                send(out,message)


    def start(self):
        self.started = True
        self._osc_server.add_method('/muse/eeg', None,self._update_eeg_liblo_osc)
        self._osc_server.start()

    def stop(self):
        self.started = False

if __name__ == '__main__':
    FS = 256.
    EEG_b, EEG_a = ut.get_filter_coeff(FS, 6, l_freq=65, h_freq=55,method='butter')
    EEG_b2, EEG_a2 = ut.get_filter_coeff(FS, 3, l_freq=1,method='butter')
    EEG_b3, EEG_a3 = ut.get_filter_coeff(FS, 3, h_freq=40,method='butter')

    b_delta, a_delta = ut.get_filter_coeff(FS, 3, l_freq=1, h_freq=4, method='butter')
    b_theta, a_theta = ut.get_filter_coeff(FS, 3, l_freq=4, h_freq=7.5, method='butter')
    b_alpha, a_alpha = ut.get_filter_coeff(FS, 3, l_freq=7.5, h_freq=13, method='butter')
    b_beta, a_beta = ut.get_filter_coeff(FS, 3, l_freq=13, h_freq=30, method='butter')




    config = {'fs': FS,
              'n_channels': 5,
              'raw_buffer_len': int(3 * FS),
              'filt_buffer_len': int(3 * FS),
              'window_len': int(FS),
              'step': int(FS / 10),
              'filter': (EEG_b, EEG_a),
              'hpfilter': (EEG_b2, EEG_a2),
              'lpfilter': (EEG_b3, EEG_a3),
              'filter_bank': {'delta': (b_delta, a_delta), 'theta': (b_theta, a_theta), 'alpha': (b_alpha, a_alpha), 'beta': (b_beta, a_alpha)},
              'psd_window_len': int(FS),
              'psd_buffer_len': 5,
              }
    fft_server = FFTServer({'port':port},  # 'MEG', #  #
                            ({'address': oscip, 'port': oscport}),
                            ({'address': None, 'port': None}),
                           config=config,
                           device_source='muse',  #vive,  leroy
                           software_source='muselsl',
                           debug_outputs=False,
                           verbose=False)

    fft_server.start()
    while True:
        try:
            time.sleep(1)
        except:
            fft_server.stop()
            print('breaking')
            break
