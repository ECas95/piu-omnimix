#define _GNU_SOURCE
#include "am030614.h"

#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include "usb.h"

#define PIUIO_VENDOR_ID 0x0547
#define PIUIO_PRODUCT_ID 0x1002
#define PIUIOBUTTON_VENDOR_ID 0x0D2F
#define PIUIOBUTTON_PRODUCT_ID 0x1010
#define PIUIO_CTL_REQ 0xAE

struct usb_bus *usb_busses = NULL;

static struct usb_bus *bus;
static struct usb_device *piuio_dev;
static struct usb_device *button_dev;
static FILE *usb_log;

static void log_usb(const char *message)
{
    if (!usb_log) {
        usb_log = fopen("/root/mk5_usb.log", "a");
        if (usb_log) {
            setvbuf(usb_log, NULL, _IOLBF, 0);
            fprintf(usb_log, "mk5 usb logger started\n");
        }
    }
    if (usb_log) {
        fprintf(usb_log, "%s\n", message);
    }
}

static void make_device(struct usb_device **out, int vendor, int product)
{
    struct usb_device *dev = calloc(1, sizeof(*dev));
    dev->config = calloc(1, sizeof(*dev->config));
    dev->config->interface = calloc(1, sizeof(*dev->config->interface));
    dev->config->interface->altsetting = calloc(1, sizeof(*dev->config->interface->altsetting));
    dev->config->interface->altsetting->endpoint = calloc(1, sizeof(*dev->config->interface->altsetting->endpoint));
    dev->descriptor.idVendor = vendor;
    dev->descriptor.idProduct = product;
    dev->bus = bus;
    *out = dev;
}

void usb_init(void)
{
    log_usb("usb_init");
}

int usb_find_busses(void)
{
    if (!bus) {
        bus = calloc(1, sizeof(*bus));
    }
    usb_busses = bus;
    log_usb("usb_find_busses");
    return 1;
}

int usb_find_devices(void)
{
    if (!bus) {
        usb_find_busses();
    }
    if (!piuio_dev) {
        make_device(&piuio_dev, PIUIO_VENDOR_ID, PIUIO_PRODUCT_ID);
    }
    if (!button_dev) {
        make_device(&button_dev, PIUIOBUTTON_VENDOR_ID, PIUIOBUTTON_PRODUCT_ID);
    }
    piuio_dev->next = button_dev;
    button_dev->prev = piuio_dev;
    bus->devices = piuio_dev;
    bus->root_dev = piuio_dev;
    log_usb("usb_find_devices");
    return 1;
}

struct usb_bus *usb_get_busses(void)
{
    return usb_busses;
}

usb_dev_handle *usb_open(struct usb_device *dev)
{
    log_usb("usb_open");
    return (usb_dev_handle *)dev;
}

int usb_close(usb_dev_handle *dev)
{
    (void)dev;
    return 0;
}

int usb_claim_interface(usb_dev_handle *dev, int interface)
{
    (void)dev;
    (void)interface;
    return 0;
}

int usb_set_configuration(usb_dev_handle *dev, int configuration)
{
    (void)dev;
    (void)configuration;
    return 0;
}

int usb_set_altinterface(usb_dev_handle *dev, int alternate)
{
    (void)dev;
    (void)alternate;
    return 0;
}

int usb_reset(usb_dev_handle *dev)
{
    (void)dev;
    return 0;
}

static void fill_piuio_packet(char *bytes, int size)
{
    unsigned char p1 = 0xFF;
    unsigned char sys = 0xFF;
    unsigned char p2 = 0xFF;
    unsigned char extra = 0xFF;

    if (piuio_state.p1_ul) p1 &= ~0x01;
    if (piuio_state.p1_ur) p1 &= ~0x02;
    if (piuio_state.p1_center) p1 &= ~0x04;
    if (piuio_state.p1_dl) p1 &= ~0x08;
    if (piuio_state.p1_dr) p1 &= ~0x10;

    if (piuio_state.p2_ul) p2 &= ~0x01;
    if (piuio_state.p2_ur) p2 &= ~0x02;
    if (piuio_state.p2_center) p2 &= ~0x04;
    if (piuio_state.p2_dl) p2 &= ~0x08;
    if (piuio_state.p2_dr) p2 &= ~0x10;

    if (piuio_state.btn_test) sys &= ~0x02;
    if (piuio_state.btn_service) extra &= ~0x01;
    if (piuio_state.btn_coin_1) extra &= ~0x08;
    if (piuio_state.btn_coin_2) extra &= ~0x10;
    if (piuio_state.btn_clear) sys &= ~0x04;

    if (size > 0) bytes[0] = p1;
    if (size > 1) bytes[1] = sys;
    if (size > 2) bytes[2] = p2;
    if (size > 3) bytes[3] = extra;
    for (int i = 4; i < size; i++) {
        bytes[i] = 0xFF;
    }
}

int usb_control_msg(usb_dev_handle *dev, int requesttype, int request, int value, int index, char *bytes, int size, int timeout)
{
    (void)value;
    (void)index;
    (void)timeout;
    struct usb_device *udev = (struct usb_device *)dev;
    if (!udev) {
        return 0;
    }

    if (udev->descriptor.idVendor == PIUIO_VENDOR_ID &&
        udev->descriptor.idProduct == PIUIO_PRODUCT_ID &&
        (requesttype & USB_TYPE_VENDOR) &&
        request == PIUIO_CTL_REQ) {
        if ((requesttype & USB_ENDPOINT_IN) && bytes && size > 0) {
            fill_piuio_packet(bytes, size);
        }
        return 8;
    }

    if (udev->descriptor.idVendor == PIUIOBUTTON_VENDOR_ID &&
        udev->descriptor.idProduct == PIUIOBUTTON_PRODUCT_ID &&
        bytes && size > 0) {
        bytes[0] = 0xFF;
        if (size > 1) bytes[1] = 0xFF;
        return 0;
    }

    return 8;
}
