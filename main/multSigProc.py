import time
from threading import Thread

import numpy as np
from scipy import signal, interpolate
from pylsl import StreamInlet, resolve_byprop
from liblo import ServerThread, Address, Message, Bundle, send

import live_utils as ut

class FFTServer():
    def __init__(self, incoming, outgoing,  sparseOutput=None, config={}, device_source='Muse',software_source='muselsl', debug_outputs=True, verbose=False):
        self.incoming = incoming
        self.outgoing = outgoing
        self.eeg_chunk_length = 12
        self.threshold = 15
        self.conc_level = 50
        self.inc = 2
