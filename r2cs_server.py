# vim: set fileencoding=utf-8 :
# This file is licensed under the terms of the MIT license. See the file
# "LICENSE.txt" in the project root for more information.
#
# This module was developed by Daren Thomas at the assistant chair for
# Sustainable Architecture and Building Technologies (Suat) at the Institute of
# Technology in Architecture, ETH Zürich. See http://suat.arch.ethz.ch for
# more information.

"""
Provides access to the revittocitysim.py as a HTTP server. Code is adapted from
the dpv_server.py script from the Design Performance Viewer.
"""

import revittocitysim

from System import AsyncCallback
from System.Net import HttpListener, HttpListenerException, HttpListenerContext
from System.Text import Encoding
from System.Threading import Thread, ThreadStart

import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
from Autodesk.Revit.UI import IExternalEventHandler
from Autodesk.Revit.UI import ExternalEvent

import traceback


clr.AddReference('DesignPerformanceViewer')
clr.AddReference('DpvApplication')


class ContextQueue(object):
    def __init__(self):
        from System.Collections.Concurrent import ConcurrentQueue
        self.contexts = ConcurrentQueue[HttpListenerContext]()

    def __len__(self):
        return len(self.contexts)

    def append(self, c):
        self.contexts.Enqueue(c)

    def pop(self):
        success, context = self.contexts.TryDequeue()
        if success:
            return context
        else:
            raise Exception("can't pop an empty ContextQueue!")


class RevitToCitySimEventHandler(IExternalEventHandler):
    '''Handle the requests for revittocitysim and output the results.'''
    def __init__(self):
        self.contexts = ContextQueue()
        self.handlers = {'revittocitysim': self.get_revittocitysim,
                         'idf': self.get_idf,
                         'favicon.ico': self.get_favicon}

    def Execute(self, uiApplication):
        print 'RevitToCitySimEventHandler.Execute'
        while self.contexts:
            context = self.contexts.pop()
            request = context.Request
            print 'RawUrl:', request.RawUrl
            parts = request.RawUrl.split('/')[1:]
            print 'parts:', parts
            if not parts:
                parts.append('html')
            function = parts[0]
            print 'RevitToCitySimEventHandler: function:', function
            if not function in self.handlers:
                function = 'revittocitysim'
            print 'function:', function
            args = parts[1:]
            print 'args:', args
            try:
                rc, ct, data = self.handlers[function](
                    args, context.Request, uiApplication)
            except:
                traceback.print_exc()
                rc = 404
                ct = 'text/plain'
                data = 'unknown error'
            try:
                response = context.Response
                response.ContentType = ct
                response.StatusCode = rc
                buffer = Encoding.UTF8.GetBytes(data)
                response.ContentLength64 = buffer.Length
                output = response.OutputStream
                output.Write(buffer, 0, buffer.Length)
                output.Close()
            except:
                traceback.print_exc()

    def get_revittocitysim(self, args, request, uiApplication):
        '''
        returns an xml serialization of the ModelSnapshot object
        corresponding to the active document.
        '''
        content_type = 'application/xml'
        try:
            snapshot = self.take_snapshot(uiApplication)
            reload(revittocitysim)
            xml = revittocitysim.build_citysim_xml(snapshot)
            return (200, content_type, xml)
        except:
            return (404, 'text/plain',
                    'Could not create RevitToCitySim xml file: '
                    + traceback.format_exc())

    def take_snapshot(self, uiApplication):
        import DesignPerformanceViewer as dpv
        dpv = dpv.DpvApplication.DpvApplication()
        doc = uiApplication.ActiveUIDocument.Document
        #print 'taking snapshot'
        snapshot = dpv.TakeSnapshot(doc)
        return snapshot

    def get_idf(self, args, request, uiApplication):
        '''
        deserializes a ModelSnapshot from the POST and then uses the DPV
        idf writer to export the ModelSnapshot as an IDF file.
        '''
        clr.AddReference('DpvApplication')
        clr.AddReference('DesignPerformanceViewer')
        from DesignPerformanceViewer.Model import ModelSnapshotImporter
        from DesignPerformanceViewer.EnergyPlusCalculation import IdfWriter
        from System.IO import StreamReader
        from System.IO import MemoryStream
        from System.Text import Encoding

        if request.HttpMethod == 'POST':
            body = request.InputStream
            encoding = request.ContentEncoding
            reader = StreamReader(body, encoding)
            snapshot_xml = reader.ReadToEnd()

            snapshot = ModelSnapshotImporter().Import(snapshot_xml)
        elif request.HttpMethod == 'GET':
            snapshot = self.take_snapshot(uiApplication)
        else:
            return (404, 'text/plain',
                    'invalid HTTP method: ' + request.HttpMethod)
        ms = MemoryStream()
        writer = IdfWriter(ms, Encoding.UTF8)
        writer.Write(snapshot)
        ms.Position = 0
        idf = StreamReader(ms, Encoding.UTF8).ReadToEnd()
        print 'idf=', idf
        return (200, 'text/plain', idf)

    def get_favicon(self, args, request, uiApplication):
        print 'in get_favicon'
        return (404, 'text/plain', 'File not found')

    def GetName(self):
        return "RevitToCitySimEventHandler"


class SnapshotServer(object):
    def __init__(self, port, revitHandler, contexts):
        self.port = port
        self.revitHandler = revitHandler
        self.contexts = contexts

    def serve_forever(self):
        try:
            self.running = True
            self.listener = HttpListener()
            prefix = 'http://localhost:%s/' % str(self.port)
            self.listener.Prefixes.Add(prefix)
            try:
                print 'starting listener'
                self.listener.Start()
                print 'started listener'
            except HttpListenerException as ex:
                print 'HttpListenerException:', ex
                return
            waiting = False
            while self.running:
                #print 'waiting:', waiting
                if not waiting:
                    context = self.listener.BeginGetContext(
                        AsyncCallback(self.handleRequest),
                        self.listener)
                waiting = not context.AsyncWaitHandle.WaitOne(100)
        except:
            traceback.print_exc()

    def stop(self):
        print 'stop()'
        self.running = False
        self.listener.Stop()
        self.listener.Close()

    def handleRequest(self, result):
        '''
        pass the request to the RevitEventHandler
        '''
        try:
            listener = result.AsyncState
            if not listener.IsListening:
                return
            try:
                context = listener.EndGetContext(result)
            except:
                # Catch the exception when the thread has been aborted
                self.stop()
                return
            self.contexts.append(context)
            self.revitHandler.Raise()
            print 'raised revitHandler'
        except:
            traceback.print_exc()


def get_revit():
    """be nice to pyflakes, it's only a machine!
    """
    import __builtin__
    return __builtin__.__revit__


def main():
    port = 8014
    print 'starting server on port: %d' % port
    revitEventHandler = RevitToCitySimEventHandler()
    externalEvent = ExternalEvent.Create(revitEventHandler)
    server = SnapshotServer(port, externalEvent, revitEventHandler.contexts)
    serverThread = Thread(ThreadStart(server.serve_forever))
    serverThread.Start()
    print 'started server thread'

    def closing(s, a):
        server.stop()
        return
    __window__.FormClosing += closing  # NOQA
    #__window__.Visible = False

if __name__ == '__main__':
    try:
        main()
    except:
        traceback.print_exc()
        __window__.Visible = True  # NOQA
