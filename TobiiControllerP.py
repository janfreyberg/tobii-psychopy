#!/usr/bin/python
#
# Tobii controller for PsychoPy
# author: Hiroyuki Sogo
#         Modified by Soyogu Matsushita
# - Tobii SDK 3.0 is required
# - no guarantee
#

# MODIFIED: tobii.sdk -> tobii.eye_tracking_io
from tobii.eye_tracking_io.basic import EyetrackerException

import os
import datetime
import time

# MODIFIED: tobii.sdk -> tobii.eye_tracking_io
import tobii.eye_tracking_io.mainloop
import tobii.eye_tracking_io.browsing
import tobii.eye_tracking_io.eyetracker
import tobii.eye_tracking_io.time.clock
import tobii.eye_tracking_io.time.sync

from tobii.eye_tracking_io.types import Point2D, Blob

import psychopy.visual
import psychopy.event

import Image
import ImageDraw


class TobiiController:

    def __init__(self, win):
        self.eyetracker = None
        self.eyetrackers = {}
        self.win = win
        self.gazeData = []
        self.eventData = []
        self.datafile = None

        tobii.eye_tracking_io.init()
        self.clock = tobii.eye_tracking_io.time.clock.Clock()
        self.mainloop_thread = tobii.eye_tracking_io.mainloop.MainloopThread()
        self.mainloop_thread.start()
        self.browser = tobii.eye_tracking_io.browsing.EyetrackerBrowser(
            self.mainloop_thread, self.on_eyetracker_browser_event)

    def waitForFindEyeTracker(self):
        while len(self.eyetrackers.keys()) == 0:
            time.sleep(0.01)

    def on_eyetracker_browser_event(self,
                                    event_type,
                                    event_name,
                                    eyetracker_info):
        # When a new eyetracker is found we add it to the treeview and to the
        # internal list of eyetracker_info objects
        if event_type == tobii.eye_tracking_io.browsing.EyetrackerBrowser.FOUND:
            self.eyetrackers[eyetracker_info.product_id] = eyetracker_info
            return False

        # Otherwise we remove the tracker from the treeview and the
        # eyetracker_info list...
        del self.eyetrackers[eyetracker_info.product_id]

        # ...and add it again if it is an update message
        if event_type ==
        tobii.eye_tracking_io.browsing.EyetrackerBrowser.UPDATED:
            self.eyetrackers[eyetracker_info.product_id] = eyetracker_info
        return False

    def destroy(self):
        self.eyetracker = None
        self.browser.stop()
        self.browser = None
        self.mainloop_thread.stop()

    ############################################################################
    # activation methods
    ############################################################################
    def activate(self, eyetracker):
        eyetracker_info = self.eyetrackers[eyetracker]
        print "Connecting to:", eyetracker_info
        (tobii.eye_tracking_io.
         eyetracker.Eyetracker.
         create_async(self.mainloop_thread,
                      eyetracker_info, lambda error,
                      eyetracker: self.on_eyetracker_created(error,
                                                             eyetracker,
                                                             eyetracker_info)))

        while self.eyetracker is None:
            time.sleep(0.01)
        self.syncmanager = tobii.eye_tracking_io.time.sync.SyncManager(
            self.clock, eyetracker_info, self.mainloop_thread)

    def on_eyetracker_created(self, error, eyetracker, eyetracker_info):
        if error:
            print ("Connection to %s failed because "
                   "of an exception: %s") % (eyetracker_info, error)
            if error == 0x20000402:
                print ("The selected unit is too old, a unit which "
                       "supports protocol version 1.0 is required.\n\n"
                       "<b>Details:</b> <i>%s</i>") % error
            else:
                print "Could not connect to %s" % (eyetracker_info)
            return False

        self.eyetracker = eyetracker

    ############################################################################
    # calibration methods
    ############################################################################

    def doCalibration(self, calibrationPoints, calinRadius=None,
                      caloutRadius=None, moveFrames=120):
        if self.eyetracker is None:
            return

        # set default
        if calinRadius is None:
            calinRadius = 2.0
        if caloutRadius is None:
            caloutRadius = calinRadius * 20.0

        self.points = calibrationPoints

        # Make the "inner" circle
        self.calin = psychopy.visual.Circle(self.win, radius=calinRadius,
                                            fillColor=(0.0, 0.0, 0.0),
                                            units='pix')
        # Make the "outer" circle
        self.calout = psychopy.visual.Circle(self.win, radius=caloutRadius,
                                             lineColor=(0.0, 1.0, 0.0),
                                             units='pix')
        # Make a dummy message
        self.calmsg = psychopy.visual.TextStim(self.win,
                                               pos=(0, -self.win.size[1] / 4))

        self.initcalibration_completed = False
        print "StartCalibration"
        self.eyetracker.StartCalibration(self.on_calib_start)
        while not self.initcalibration_completed:
            core.wait(0.1)

        # Draw instructions and wait for space key
        self.calmsg.text = ("Press space when you're ready")
        self.calinstruction.draw()
        self.win.flip()
        psychopy.event.waitKeys(keyList=['space'])

        # Go through the calibration points
        for self.point_index in range(len(self.points)):
            # The dot starts at the previous point
            self.calin.pos =
            self.calout.pos = ((self.points[self.point_index - 1][0] - 0.5) *
                               self.win.size[0],
                               (self.points[self.point_index - 1][1] - 0.5) *
                               self.win.size[1])
            # The steps for the movement is new - old divided by frames
            self.step = (((self.points[self.point_index][0] - 0.5) *
                          self.win.size[0],
                          (self.points[self.point_index][1] - 0.5) *
                          self.win.size[1]) - self.calout.pos) / moveFrames

            # Create a tobii 2D class
            p = Point2D()
            # Add the X and Y coordinates to the tobii point
            p.x, p.y = self.points[self.point_index]

            # Move the point in position (smooth pursuit)
            for frame in range(moveFrames):
                self.calin.pos =
                self.calout.pos += self.step
                # draw & flip
                self.calin.draw()
                self.calout.draw()
                self.win.flip()

            # Shrink the outer point (gaze fixation)
            for frame in range(moveFrames / 2):
                self.calout.radius -= (caloutRadius -
                                       calinRadius) / (moveFrames / 2)
                self.calout.draw()
                self.calin.draw()
                self.win.flip()

            # Add this point to the tobii
            self.add_point_completed = False  # this gets updated automatically
            self.eyetracker.AddCalibrationPoint(p, self.on_add_completed)
            # While this point is being added, do nothing:
            while not self.add_point_completed:
                core.wait(0.1)

            # Reset the radius of the large circle
            self.calout.radius = caloutRadius

        # The following two will be set by the tobii SDK
        self.computeCalibration_completed =
        self.computeCalibration_succeeded = False
        # Do the computation
        self.eyetracker.ComputeCalibration(self.on_calib_compute)
        while not self.computeCalibration_completed:
            core.wait(0.1)
        self.eyetracker.StopCalibration(None)

        self.win.flip()

        # Now we retrieve the calibration data
        self.getcalibration_completed = False
        self.calib = self.eyetracker.GetCalibration(self.on_calib_response)
        while not self.getcalibration_completed:
            core.wait(0.1)

        if not self.computeCalibration_succeeded:
            # computeCalibration failed.
            self.calmsg.text = ("Not enough data was collected "
                                "(Retry:[r] Abort:[ESC])")
        elif self.calib is None:
            # no calibration data
            self.calmsg.text = ("No calibration data "
                                "(Retry:[r] Abort:[ESC])")
        else:
            # calibration seems to have worked out
            points = {}
            for data in self.calib.plot_data:
                points[data.true_point] = {
                    'left': data.left, 'right': data.right}

            if len(points) == 0:
                # no points in the calibration results
                self.calmsg.text = ("No calibration data "
                                    "(Retry:[r] Abort:[ESC])")
            else:
                # draw the calibration result
                for p, d in points.iteritems():
                    # draw the calibration results onto ImageDraw.
                    # TODO: Remove ImageDraw, use psychopy instead.
                    if d['left'].status == 1:
                        psychopy.visual.Line(self.win, units='pix',
                                             lineColor='red',
                                             start=(p.x * self.win.size[0],
                                                    p.y * self.win.size[1]),
                                             end=(d['left'].map_point.x *
                                                  self.win.size[0],
                                                  d['left'].map_point.y *
                                                  self.win.size[1])).draw()
                    if d['right'].status == 1:
                        psychopy.visual.Line(self.win, units='pix',
                                             lineColor='red',
                                             start=(p.x * self.win.size[0],
                                                    p.y * self.win.size[1]),
                                             end=(d['right'].map_point.x *
                                                  self.win.size[0],
                                                  d['right'].map_point.y *
                                                  self.win.size[1])).draw()
                self.calmsg.text = ("Accept calibration results\n"
                                    "(Accept:[a] Retry:[r] Abort:[ESC])")

        # Update the screen, then wait for response
        self.calmsg.draw()
        self.win.flip()
        self.response = psychopy.event.waitKeys(keyList=['a', 'r', 'escape'])
        if 'a' in self.response:
            retval = 'accept'
        elif 'r' in self.response:
            retval = 'retry'
        elif 'escape' in response:
            retval = 'abort'

        return retval

    def on_calib_start(self, error, r):
        if error:
            print ("Could not start calibration because of error "
                   "(0x%0x)" % error)
            return False
        self.initcalibration_completed = True

    def on_add_completed(self, error, r):
        if error:
            print ("Add Calibration Point failed because of error "
                   "(0x%0x)" % error)
            return False

        self.add_point_completed = True
        return False

    def on_calib_compute(self, error, r):
        if error == 0x20000502:
            print ("CalibCompute failed because not enough data was "
                   "collected:"), error
            print "Not enough data was collected during calibration procedure."
            self.computeCalibration_succeeded = False
        elif error != 0:
            print "CalibCompute failed because of a server error:", error
            print ("Could not compute calibration because of a server "
                   "error.\n\n<b>Details:</b>\n<i>%s</i>") % (error)
            self.computeCalibration_succeeded = False
        else:
            print ""
            self.computeCalibration_succeeded = True

        self.computeCalibration_completed = True
        return False

    def on_calib_response(self, error, calib):
        if error:
            print "On_calib_response: Error =", error
            self.calib = None
            self.getcalibration_completed = True
            return False

        print "On_calib_response: Success"
        self.calib = calib
        self.getcalibration_completed = True
        return False

    def on_calib_done(self, status, msg):
        # When the calibration procedure is done we update the calibration plot
        if not status:
            print msg

        self.calibration = None
        return False

    ############################################################################
    # tracking methods
    ############################################################################
    def startTracking(self):
        self.gazeData = []
        self.eventData = []
        self.eyetracker.events.OnGazeDataReceived += self.on_gazedata
        self.eyetracker.StartTracking()

    def stopTracking(self):
        self.eyetracker.StopTracking()
        self.eyetracker.events.OnGazeDataReceived -= self.on_gazedata
        self.flushData()
        self.gazeData = []
        self.eventData = []

    def on_gazedata(self, error, gaze):
        self.gazeData.append(gaze)

    def getGazePosition(self, gaze):
        return ((gaze.LeftGazePoint2D.x - 0.5) * self.win.size[0],
                (0.5 - gaze.LeftGazePoint2D.y) * self.win.size[1],
                (gaze.RightGazePoint2D.x - 0.5) * self.win.size[0],
                (0.5 - gaze.RightGazePoint2D.y) * self.win.size[1])

    def getCurrentGazePosition(self):
        if len(self.gazeData) == 0:
            return (None, None, None, None)
        else:
            return self.getGazePosition(self.gazeData[-1])

    def setDataFile(self, filename):
        print 'set datafile ' + filename
        self.datafile = open(filename, 'w')
        self.datafile.write('Recording date:\t' +
                            datetime.datetime.now().strftime('%Y/%m/%d') + '\n')
        self.datafile.write('Recording time:\t' +
                            datetime.datetime.now().strftime('%H:%M:%S') + '\n')
        self.datafile.write('Recording resolution\t%d x %d\n\n' %
                            tuple(self.win.size))

    def closeDataFile(self):
        print 'datafile closed'
        if self.datafile is not None:
            self.flushData()
            self.datafile.close()

        self.datafile = None

    def recordEvent(self, event):
        t = self.syncmanager.convert_from_local_to_remote(self.clock.get_time())
        self.eventData.append((t, event))

    def flushData(self):
        if self.datafile is None:
            print 'data file is not set.'
            return

        if len(self.gazeData) == 0:
            return

        self.datafile.write('\t'.join(['TimeStamp',
                                       'GazePointXLeft',
                                       'GazePointYLeft',
                                       'ValidityLeft',
                                       'GazePointXRight',
                                       'GazePointYRight',
                                       'ValidityRight',
                                       'GazePointX',
                                       'GazePointY',
                                       'Event']) + '\n')
        timeStampStart = self.gazeData[0].Timestamp
        for g in self.gazeData:
            self.datafile.write('%.1f\t%.4f\t%.4f\t%d\t%.4f\t%.4f\t%d' % (
                                (g.Timestamp - timeStampStart) / 1000.0,
                                g.LeftGazePoint2D.x *
                                self.win.size[
                                    0] if g.LeftValidity != 4 else -1.0,
                                g.LeftGazePoint2D.y *
                                self.win.size[
                                    1] if g.LeftValidity != 4 else -1.0,
                                g.LeftValidity,
                                g.RightGazePoint2D.x *
                                self.win.size[
                                    0] if g.RightValidity != 4 else -1.0,
                                g.RightGazePoint2D.y *
                                self.win.size[
                                    1] if g.RightValidity != 4 else -1.0,
                                g.RightValidity))
            if g.LeftValidity == 4 and g.RightValidity == 4:  # not detected
                ave = (-1.0, -1.0)
            elif g.LeftValidity == 4:
                ave = (self.win.size[0] * g.RightGazePoint2D.x,
                       self.win.size[1] * g.RightGazePoint2D.y)
            elif g.RightValidity == 4:
                ave = (self.win.size[0] * g.LeftGazePoint2D.x,
                       self.win.size[1] * g.LeftGazePoint2D.y)
            else:
                ave = (self.win.size[0] * (g.LeftGazePoint2D.x +
                                           g.RightGazePoint2D.x) / 2.0,
                       self.win.size[1] * (g.LeftGazePoint2D.y +
                                           g.RightGazePoint2D.y) / 2.0)

            self.datafile.write('\t%.4f\t%.4f\t' % ave)
            self.datafile.write('\n')

        formatstr = '%.1f' + '\t' * 9 + '%s\n'
        for e in self.eventData:
            self.datafile.write(formatstr %
                                ((e[0] - timeStampStart) / 1000.0, e[1]))

        self.datafile.flush()

############################################################################
# run following codes if this file is executed directly
############################################################################

if __name__ == "__main__":
    import sys

    win = psychopy.visual.Window(size=(1280, 1024), fullscr=True, units='pix')
    controller = TobiiController(win)
    controller.setDataFile('testdata.tsv')

    controller.waitForFindEyeTracker()
    controller.activate(controller.eyetrackers.keys()[0])

    while True:
        ret = controller.doCalibration(
            [(0.1, 0.1), (0.9, 0.1), (0.5, 0.5), (0.1, 0.9), (0.9, 0.9)])
        if ret == 'accept':
            break
        elif ret == 'abort':
            controller.destroy()
            sys.exit()

    marker = psychopy.visual.Rect(win, width=5, height=5)

    controller.startTracking()

    waitkey = True
    while waitkey:
        currentGazePosition = controller.getCurrentGazePosition()
        if None not in currentGazePosition:
            marker.setPos(currentGazePosition[0:2])
        for key in psychopy.event.getKeys():
            if key == 'space':
                waitkey = False
            elif key == 'w':
                controller.recordEvent('w key')

        marker.draw()
        win.flip()

    controller.stopTracking()
    win.close()
    controller.closeDataFile()
    controller.destroy()
