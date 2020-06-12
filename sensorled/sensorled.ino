#include <SPI.h>
#include "mcp_can.h"

/* Input and output pins for ultrasonic sensor */
#define PIN_TRIG        5
#define PIN_ECHO        6

/* Pins to turn on LED (2 pins to step up voltage from 3V to 6V) */
#define PIN_LED         7
#define PIN_LED2        8

// the cs pin of the version after v1.1 is default to D9
// v0.9b and v1.0 is default D10
const int SPI_CS_PIN = 10;

MCP_CAN CAN(SPI_CS_PIN);                                    // Set CS pin


/* readDist
 *  DESCRIPTION: Controls ultrasonic sensor to find closest object in front
 *    of it and return the distance to that object.
 *  INPUTS: none
 *  OUTPUTS: distance in centimeters.
 */
int readDist() {
  /* Clear the sensor trigger pin and delay for 3 microseocnds */
  digitalWrite(PIN_TRIG, LOW);
  delayMicroseconds(2);

  /* Send a signal from the trigger pin for 10 microseconds */
  digitalWrite(PIN_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(PIN_TRIG, LOW);

  /* Read distance from echo pin and convert to cm */
  return pulseIn(PIN_ECHO, HIGH) * (0.034 / 2);
}


/* willBrake
 *  DESCRIPTION: Checks if incoming packet is a valid PI packet by checking
 *    if the first three bytes are 'PI:' and returns a 1 if the fourth incoming
 *    byte is 1 denoting to send a brake signal otherwise return 0 if the 
 *    fourth byte is 0.
 *  INPUTS: len - lenght of incoming packet
 *          buf - 
 *  OUTPUTS: 1 - send brake signal
 *           0 - don't send brake signal
 *          -1 - invalid packet
 */
int willBrake(unsigned char len, unsigned char * buf) {
  if (len <= 3 || strncmp("PI:", buf, 3)) { return -1; }
  return (buf[3]) ? 1 : 0;
}


/* intToChar
 *  DESCRIPTION: Converts integer to unsigned char buffer
 *  INPUTS: dist - distance
 *          sendBuf - unsigned char buffer
 *  OUTPUTS: none
 */
void intToChar(int dist, unsigned char sendBuf[8]) {
  int n = log10(dist) + 1;

  memset(sendBuf, 0, 8);  // clear buffer
  for (int i = 0; i < n; ++i, dist /= 10) {
    sendBuf[i] = dist % 10;
  }
}


void setup() {
  Serial.begin(115200);

  /* Initialize echo and trigger pins for sensor */
  pinMode(PIN_TRIG, OUTPUT);
  pinMode(PIN_ECHO, INPUT);

  /* Initialize CAN bus conneciton */
  while (CAN_OK != CAN.begin(CAN_500KBPS))              // init can bus : baudrate = 500k
  {
      Serial.println("CAN BUS Shield init fail");
      Serial.println(" Init CAN BUS Shield again");
      delay(100);
  }
  Serial.println("CAN BUS Shield init ok!");
}


void loop() {
  int dist;
  unsigned char len = 0;
  unsigned char buf[1] = {0};
  unsigned char sendBuf[3] = {0, 0, 0};

  /* Read distance from ultrasonic sensor and convert to char buffer */
  dist = readDist();
  Serial.print("Distance: ");
  Serial.println(dist);

  if (dist > 400) {
    dist = 400;
  } else if (dist < 1) {
    dist = 1;
  }

  /* Convert the distance, into a array of the char representation of it's digits
   * to send to the CAN to IP gateway. 
   * Ex: distance = 12 gets converted to {'2', '1', '0'}
   * Ex2: distance = 214 gets converted to {'4', '1', '2'}
   */
  sendBuf[0] = (dist % 10) + '0';
  dist = dist/10;
  sendBuf[1] = (dist % 10) + '0';
  dist = dist/10;
  sendBuf[2] = (dist % 10) + '0';


  /* Send distance via CAN connection */
  CAN.sendMsgBuf(0x00, 0, 3, sendBuf);


  /* Check for incoming data (brake LED) from the CAN to IP gateway Arduino */
  if(CAN_MSGAVAIL == CAN.checkReceive())
  {
      CAN.readMsgBuf(&len, buf);    // read data,  len: data length, buf: data buf

      unsigned long canId = CAN.getCanId();
      
      Serial.println("-----------------------------");
      Serial.print("Get data from ID: 0x");
      Serial.println(canId, HEX);

      for(int i = 0; i<len; i++)    // print the data
      {
          Serial.print(buf[i], HEX);
          Serial.print("\t");
      }
      
      /* Decide whether or not to signal a brake */
      if (buf[0] == 1) {
        Serial.println("brake");
        digitalWrite(PIN_LED, HIGH);
        digitalWrite(PIN_LED2, HIGH);
        // let LED stay turned on 100 ms (ie, keep braking)
        delay(100);
      } else if (buf[0] == 0) {
        digitalWrite(PIN_LED, LOW);
        digitalWrite(PIN_LED2, LOW);
      }
   }
    
   delay(100);
    
}
