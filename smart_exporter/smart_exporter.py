# -*- coding: utf-8 -*-
import gevent.monkey
gevent.monkey.patch_all()  # noqa

import logging

from flask import Flask
from gevent.wsgi import WSGIServer
import prometheus_client
from werkzeug.wsgi import DispatcherMiddleware
import pySMART as pysmart


logger = logging.getLogger(__name__)


class SMARTMetrics(object):
    def __init__(self, prom_app, registry):
        self.registry = registry
        self.prom_app = prom_app

        self.attributes = prometheus_client.Gauge('smart_attribute', 'SMART attributes by device', ['serial', 'attribute_name'], registry=self.registry)
        self.devices = {}
        self.label_cache = {}
        self.refresh_devices()

    @staticmethod
    def devices_by_serial(device_list):
        return {
            device.serial: device
            for device
            in device_list
        }

    def handle_metrics(self, environ, start_response):
        self.refresh_devices()
        return self.prom_app(environ, start_response)

    def clear_labels(self, serials):
        for serial in serials:
            print 'Removing {}'.format(serial)
            cache = self.label_cache[serial]
            for attribute_name in cache.iterkeys():
                print 'Removing {}:{}'.format(serial, attribute_name)
                self.attributes.remove(serial, attribute_name)
            del self.label_cache[serial]

    def update_metrics(self):
        for serial, device in self.devices.iteritems():
            if serial not in self.label_cache:
                print 'Adding {}'.format(serial)
                self.label_cache[serial] = {}
            metrics = self.label_cache[serial]
            for attribute in device.attributes:
                if attribute is None:
                    continue
                metrics = self.label_cache[serial]
                if attribute.name not in metrics:
                    metrics[attribute.name] = self.attributes.labels(serial, attribute.name)
                metric = metrics[attribute.name]
                metric.set(int(attribute.raw))

    def refresh_devices(self):
        new_devices = self.devices_by_serial(pysmart.DeviceList().devices)

        old_serials = set(self.devices.keys())
        new_serials = set(new_devices.keys())

        removed_serials = old_serials - new_serials
        added_serials = new_serials - old_serials

        print removed_serials

        # Clean up metrics
        self.clear_labels(removed_serials)

        # Refresh metrics
        self.devices = new_devices
        self.update_metrics()


class SMARTApp(Flask):
    def __init__(self):
        Flask.__init__(self, __name__)
        self.add_url_rule('/', view_func=self.index)

    def index(self):
        return 'root'


def main():
    registry = prometheus_client.REGISTRY
    prom_app = prometheus_client.make_wsgi_app(registry)
    smart = SMARTMetrics(prom_app, registry)
    app = SMARTApp()
    wsgi_app = DispatcherMiddleware(
        app.wsgi_app,
        {
            '/metrics': smart.handle_metrics,
        },
    )
    server = WSGIServer(('127.0.0.1', 9291), wsgi_app)
    server.serve_forever()
