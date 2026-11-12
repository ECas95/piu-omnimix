#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
#include "channel_policy.h"

int main(void) {
    uint32_t songs[12*9]={0}, charts[12*9]={0};
    for(unsigned i=1;i<=10;i++) {
        songs[i*9]=0xa1000000u+i;
        songs[i*9+5]=(0x16+i)|0x01020000u;
        charts[i*9]=(i<<16)|i;
        charts[i*9+1]=i;
        charts[i*9+2]=0x00200101u;
    }
    for(unsigned channel=0;channel<=0x38;channel++) {
        apply_channel_policy(songs,12,charts,12,channel,0);
        for(unsigned i=1;i<=10;i++)
            assert(!!(charts[i*9+2]&0x00800000u)==(channel==0x2e + i));
    }
    // Each Anime volume must own its own records in Basic probes too.
    for(unsigned channel=0x35;channel<=0x38;channel++) {
        apply_channel_policy(songs,12,charts,12,channel,1);
        for(unsigned i=1;i<=10;i++)
            assert(!!(charts[i*9+2]&0x00800000u)==(channel==0x2e + i));
    }
    // Removing a chart payload must remove that chart from every channel.
    charts[10*9+1]=UINT32_MAX;
    apply_channel_policy(songs,12,charts,12,0x38,0);
    assert(!(charts[10*9+2]&0x00800000u));
    puts("PASS: ten imported channels isolated, four Anime filters in Full/Basic, missing chart excluded");
    return 0;
}

