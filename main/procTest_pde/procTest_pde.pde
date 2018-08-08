import oscP5.*;
OscP5 oscP5;
int counter = 0;

void setup(){
  size(400,400);
  oscP5 = new OscP5(this,8001); 
}

void draw(){
  background(0);
}
void oscEvent(OscMessage theOscMessage){
    if(theOscMessage.checkAddrPattern("/")==true) {
        //if(theOscMessage.checkTypetag("ifs")) {
          //int firstValue = theOscMessage.get(0).intValue();  // get the first osc argument
          //float secondValue = theOscMessage.get(1).floatValue(); // get the second osc argument
          //String thirdValue = theOscMessage.get(2).stringValue(); // get the third osc argument
          //print("### received an osc message /test with typetag ifs.");
          //println(" values: "+firstValue+", "+secondValue+", "+thirdValue);
          //return;
          println(theOscMessage);

        //}
    }
}
