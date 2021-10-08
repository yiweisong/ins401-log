#include "stdint.h"

uint16_t calc_crc (uint8_t *buf, uint32_t length);

uint16_t calc_crc (uint8_t *buf, uint32_t length)
{
	uint16_t crc = 0x1D0F;  //non-augmented inital value equivalent to the augmented initial value 0xFFFF
	int i, j;
	for (int i=0; i < length; i++) {
		crc ^= buf[i] << 8;
		
		for (int j=0; j<8; j++) {
			if (crc & 0x8000) {
                crc = (crc << 1) ^ 0x1021;
            }
			else {
                crc = crc << 1;
            }
		}
	}
	
	return crc & 0xffff;
}