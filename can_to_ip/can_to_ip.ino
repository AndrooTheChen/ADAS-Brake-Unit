#include <SPI.h>
#include <Ethernet.h>
#include <EthernetUdp.h>
#include "mcp_can.h"

const int SPI_CS_PIN = 10;

byte mac[] = {
  0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0xED
};

// CAN to IP arduino's IP
IPAddress ip(10, 0, 0, 3);

// Raspi IP
IPAddress remote(10, 0, 0, 2);

// CAN to IP arduino listening port
unsigned int localPort = 8888;  

// Port of raspi to which distance data is sent to 
unsigned int remPort = 9000;

MCP_CAN CAN(SPI_CS_PIN);                                    

// An EthernetUDP instance to let us send and receive packets over UDP
EthernetUDP Udp;

void setup()
{
    Serial.begin(115200);
    Ethernet.begin(mac, ip);
    while (!Serial) {
      ; // wait for serial port to connect. Needed for native USB port only
    }

    // init can bus : baudrate = 500k
    while (CAN_OK != CAN.begin(CAN_500KBPS))              
    {
        Serial.println("CAN BUS Shield init fail");
        Serial.println(" Init CAN BUS Shield again");
        delay(100);
    }
    Serial.println("CAN BUS Shield init ok!");

    // Initialize ethernet hardware
    if (Ethernet.hardwareStatus() == EthernetNoHardware) {
      Serial.println("Ethernet shield was not found.  Sorry, can't run without hardware. :(");
      while (true) {
        delay(1); // do nothing, no point running without Ethernet hardware
      }
    }
    if (Ethernet.linkStatus() == LinkOFF) {
      Serial.println("Ethernet cable is not connected.");
    }

    // start UDP
    Udp.begin(localPort); 
}

// Char sent to the ECU arduino to indicate whether or not to brake
unsigned char brake_on[1] = {1};
unsigned char brake_off[1] = {0};

void loop()
{
    unsigned char len = 0;
    unsigned char buf[3];
    char packetBuffer[UDP_TX_PACKET_MAX_SIZE];  
    
    // receive distance data from CAN Arduino
    if(CAN_MSGAVAIL == CAN.checkReceive())            // check if data coming
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
         Serial.println();

        char replyBuf[] = {buf[0], buf[1], buf[2]};

        // send this data to the raspi
        Udp.beginPacket(remote, remPort);
        Udp.write(replyBuf);
        Udp.endPacket();
    }

    // receive brake signal from the raspberry pi
    // the raspi either sends RP0 (for don't brake) or RP1 for brake
    int packetSize = Udp.parsePacket();
    if (packetSize) {
        // read the packet into packetBufffer
        Udp.read(packetBuffer, UDP_TX_PACKET_MAX_SIZE);
        Serial.println("Contents:");
        Serial.println(packetBuffer);
    }

    // send brake signal over to the CAN Arduino
    if((packetBuffer[0] == 'R') && (packetBuffer[1] == 'P') && ((packetBuffer[2] - '0') == 1)) {
          CAN.sendMsgBuf(0x00, 0, 1, brake_on);
    } else if ((packetBuffer[0] == 'R') && (packetBuffer[1] == 'P') && ((packetBuffer[2] - '0') == 0)) {
          CAN.sendMsgBuf(0x00, 0, 1, brake_off);
    }

    delay(350); 
}
