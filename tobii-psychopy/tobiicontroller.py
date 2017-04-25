#!/usr/bin/python
#
# Tobii controller for PsychoPy
# author: Hiroyuki Sogo
#         Modified by Soyogu Matsushita
#         Further modified by Jan Freyberg
# - Tobii SDK 3.0 is required
# - no guarantee
#

from tobii.eye_tracking_io.basic import EyetrackerException

import datetime

import tobii.eye_tracking_io.mainloop
import tobii.eye_tracking_io.browsing
import tobii.eye_tracking_io.eyetracker
import tobii.eye_tracking_io.time.clock
import tobii.eye_tracking_io.time.sync

from tobii.eye_tracking_io.types import Point2D

import psychopy.visual
import psychopy.event
import psychopy.core
import psychopy.monitors
from psychopy.tools.monitorunittools import deg2pix

import numpy as np


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
            psychopy.core.wait(0.1)
            if psychopy.event.getKeys(keyList=['escape']):
                raise KeyboardInterrupt("You interrupted the script.")

    def on_eyetracker_browser_event(self,
                                    event_type,
                                    event_name,
                                    eyetracker_info):
        # When a new eyetracker is found we add it to the treeview and to the
        # internal list of eyetracker_info objects
        if event_type is tobii.eye_tracking_io.browsing.EyetrackerBrowser.FOUND:
            self.eyetrackers[eyetracker_info.product_id] = eyetracker_info
            return False

        # Otherwise we remove the tracker from the treeview and the
        # eyetracker_info list...
        del self.eyetrackers[eyetracker_info.product_id]

        # ...and add it again if it is an update message
        if event_type is (tobii.eye_tracking_io.browsing.
                          EyetrackerBrowser.UPDATED):
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
            psychopy.core.wait(0.1)
            if psychopy.event.getKeys(keyList=['escape']):
                raise KeyboardInterrupt("You interrupted the script.")
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

    def findEyes(self):
        # This method starts tracking, finds eyes, and then displays the
        # eyes on the screen for the researcher to see.
        if self.eyetracker is None:
            return

        # Set default colors
        self.correctColor = (-1.0, 1.0, -1.0)
        self.mediumColor = (-1.0, 1.0, 1.0)
        self.wrongColor = (1.0, -1.0, -1.0)

        # Make a dummy message
        self.findmsg = psychopy.visual.TextStim(self.win, color=0.0,
                                                units='norm', pos=(0.0, -0.8),
                                                height=0.07)
        self.findmsg.setAutoDraw(True)
        # Make stimuli for the left and right eye
        self.leftStim = psychopy.visual.Circle(self.win,
                                               fillColor=1.0, units='cm',
                                               radius=0.5, autoDraw=True)
        self.rightStim = psychopy.visual.Circle(self.win,
                                                fillColor=1.0,
                                                units='cm',
                                                radius=0.5, autoDraw=True)
        # Make a rectangle in the middle to get eyes into
        self.eyeArea = psychopy.visual.Rect(self.win, lineColor=(0, 1, 0),
                                            units='norm', lineWidth=3,
                                            width=0.5, height=0.5,
                                            autoDraw=True)
        # Start tracking
        self.datafile = None  # we don't want to save this data
        self.startTracking()
        psychopy.core.wait(0.1)
        self.response = []
        while not self.response:
            self.lxyz, self.rxyz = self.getCurrentEyePosition()
            # update the left eye if the values are reasonable
            self.leftStim.pos = (self.lxyz[0] / 10,
                                 self.lxyz[1] / 10)
            # update the right eye if the values are reasonable
            self.rightStim.pos = (self.rxyz[0] / 10,
                                  self.rxyz[1] / 10)
            # update the distance if the values are reasonable
            self.distance = np.mean([self.lxyz[2], self.rxyz[2]]) / 10
            if self.distance > 56 and self.distance < 64:
                # correct distance
                self.findmsg.color = (-1, 1, -1)
            else:
                # not really correct
                self.findmsg.color = (1, 1, 0.2)
            self.findmsg.text = "You're currently " + \
                                str(int(self.distance)) + \
                                ("cm away from the screen.\n"
                                 "Press space to calibrate or "
                                 "esc to abort.")
            self.win.flip()
            self.response = psychopy.event.getKeys(keyList=['space', 'escape'])
            psychopy.core.wait(0.01)
        # Once responded, stop tracking
        self.stopTracking()
        if 'escape' in self.response:
            raise KeyboardInterrupt("You interrupted the script manually.")
        else:
            # destroy the feedback stimuli and return (empty)
            self.eyeArea.setAutoDraw(False)
            self.leftStim.setAutoDraw(False)
            self.rightStim.setAutoDraw(False)
            self.findmsg.setAutoDraw(False)
            self.leftStim = self.rightStim = self.findmsg = None
            self.win.flip()
            return

    def doCalibration(self, calibrationPoints=[(0.5, 0.5), (0.1, 0.9),
                                               (0.1, 0.1), (0.9, 0.9),
                                               (0.9, 0.1)],
                      calinRadius=2.0, caloutRadius=None, moveFrames=60):
        if self.eyetracker is None:
            return

        # set default
        if caloutRadius is None:
            caloutRadius = calinRadius * 20.0
        if calibrationPoints is None:
            calibrationPoints = [(0.5, 0.5), (0.1, 0.9),
                                 (0.1, 0.1), (0.9, 0.9), (0.9, 0.1)]

        self.points = np.random.permutation(calibrationPoints)

        # Make the "outer" circle
        self.calout = psychopy.visual.Circle(self.win, radius=caloutRadius,
                                             lineColor=(0, 1.0, 0),
                                             fillColor=(0.5, 1.0, 0.5),
                                             units='pix', autoDraw=True,
                                             pos=self.acsd2pix(self.points[-1]))
        # Make a dummy message
        self.calmsg = psychopy.visual.TextStim(self.win, color=0.0,
                                               units='norm', height=0.07,
                                               pos=(0.0, -0.5))

        # Put the eye tracker into the calibration state
        self.initcalibration_completed = False
        print "Start new calibration..."
        self.eyetracker.StartCalibration(callback=self.on_calib_start)
        while not self.initcalibration_completed:
            psychopy.core.wait(0.1)
            if psychopy.event.getKeys(keyList=['escape']):
                raise KeyboardInterrupt("You interrupted the script.")
        self.deletecalibration_completed = False
        # Clear out previous calibrations (tobii scanners
        # sometimes store these across many sessions)
        print "Delete old calibration..."
        self.eyetracker.ClearCalibration(callback=self.on_calib_deleted)
        while not self.deletecalibration_completed:
            psychopy.core.wait(0.1)
            if psychopy.event.getKeys(keyList=['escape']):
                raise KeyboardInterrupt("You interrupted the script.")

        # Draw instructions and wait for space key
        self.calmsg.text = ("Please focus your eyes on the green dot, and "
                            "follow it with your eyes when it moves. This "
                            "will help us calibrate the eye tracker.\n"
                            "Press space when you're ready.")
        self.calmsg.draw()
        self.win.flip()
        psychopy.event.waitKeys(keyList=['space'])

        # Go through the calibration points
        for self.point_index in range(len(self.points)):
            # The dot starts at the previous point
            self.calout.pos = \
                self.acsd2pix((self.points[self.point_index - 1][0],
                               self.points[self.point_index - 1][1]))
            # The steps for the movement is new - old divided by frames
            self.step = (self.acsd2pix((self.points[self.point_index][0],
                                        self.points[self.point_index][1])) -
                         self.calout.pos) / moveFrames

            # Create a tobii 2D class
            p = Point2D()
            # Add the X and Y coordinates to the tobii point
            p.x, p.y = self.points[self.point_index]

            # Move the point in position (smooth pursuit)
            for frame in range(moveFrames):
                self.calout.pos += self.step
                # draw & flip
                self.win.flip()

            # Shrink the outer point (gaze fixation)
            for frame in range(moveFrames / 2):
                self.calout.radius -= (caloutRadius -
                                       calinRadius) / (moveFrames / 2)
                self.win.flip()

            # Add this point to the tobii
            psychopy.core.wait(1)  # first wait to let the eyes settle (MIN 0.5)
            self.add_point_completed = False  # this gets updated by callback
            self.eyetracker.AddCalibrationPoint(p,
                                                callback=self.on_add_completed)
            # While this point is being added, do nothing:
            while not self.add_point_completed:
                psychopy.core.wait(0.1)
                if psychopy.event.getKeys(keyList=['escape']):
                    raise KeyboardInterrupt("You interrupted the script.")
            psychopy.core.wait(0.5)  # wait before continuing

            # Reset the radius of the large circle
            self.calout.radius = caloutRadius

        # After calibration, make sure the stimuli aren't drawn
        self.calout.autoDraw = False
        self.calout = None

        # The following two will be set by the tobii SDK
        self.computeCalibration_completed = False
        self.computeCalibration_succeeded = False
        # Do the computation
        self.eyetracker.ComputeCalibration(self.on_calib_compute)
        while not self.computeCalibration_completed:
            psychopy.core.wait(0.1)
            if psychopy.event.getKeys(keyList=['escape']):
                raise KeyboardInterrupt("You interrupted the script.")
        self.eyetracker.StopCalibration(None)

        self.win.flip()

        # Now we retrieve the calibration data
        self.getcalibration_completed = False
        self.calib = self.eyetracker.GetCalibration(self.on_calib_response)
        while not self.getcalibration_completed:
            psychopy.core.wait(0.1)
            if psychopy.event.getKeys(keyList=['escape']):
                raise KeyboardInterrupt("You interrupted the script.")

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
                points[data.true_point] = {'left': data.left,
                                           'right': data.right}

            if len(points) == 0:
                # no points in the calibration results
                self.calmsg.text = ("No calibration data "
                                    "(Retry:[r] Abort:[ESC])")
            else:
                # draw the calibration result
                for p, d in points.iteritems():
                    psychopy.visual.Circle(self.win, radius=calinRadius,
                                           fillColor=(1, 1, 1),
                                           units='pix',
                                           pos=(p.x - 0.5, 0.5 - p.y)).draw()
                    if d['left'].status == 1:
                        psychopy.visual.Line(self.win, units='pix',
                                             lineColor='yellow',
                                             start=(self.acsd2pix((p.x, p.y))),
                                             end=(self.acsd2pix((d['left'].
                                                                 map_point.x,
                                                                 d['left'].
                                                                 map_point.y)))
                                             ).draw()
                    if d['right'].status == 1:
                        psychopy.visual.Line(self.win, units='pix',
                                             lineColor='blue',
                                             start=(self.acsd2pix((p.x, p.y))),
                                             end=(self.acsd2pix((d['right'].
                                                                 map_point.x,
                                                                 d['right'].
                                                                 map_point.y)))
                                             ).draw()
                for p in self.points:
                    psychopy.visual.Circle(self.win, radius=calinRadius,
                                           fillColor=1,
                                           units='pix',
                                           pos=self.acsd2pix(p),
                                           ).draw()
                    psychopy.visual.Circle(self.win, units='pix',
                                           lineColor=-0.5,
                                           radius=deg2pix(0.9,
                                                          self.win.monitor),
                                           pos=self.acsd2pix(p),
                                           ).draw()
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
        elif 'escape' in self.response:
            retval = 'abort'

        return retval

    # The following are given as callback functions to the tobii SDK
    def on_calib_deleted(self, error, r):
        if error:
            print ("Could not delete calibration because of error "
                   "(0x%0x)" % error)
            raise ValueError("Could not delete calibration!")
        self.deletecalibration_completed = True

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
        # creates a gaze data list and starts tobii tracking, appending
        # each data point to the list
        self.gazeData = []
        self.eventData = []
        self.eyetracker.events.OnGazeDataReceived += self.on_gazedata
        self.eyetracker.StartTracking()

    def stopTracking(self):
        # stops tobii tracking, writes data to file, and empties the
        # gaze data list
        self.eyetracker.StopTracking()
        self.eyetracker.events.OnGazeDataReceived -= self.on_gazedata
        self.flushData()
        self.gazeData = []
        self.eventData = []

    def on_gazedata(self, error, gaze):
        # this gets called by tobii when its event OnGazeDataReceived fires
        self.gazeData.append(gaze)

    def getGazePosition(self, gaze):
        # returns gaze position in pixl relative to center
        return (self.acsd2pix((gaze.LeftGazePoint2D.x,
                               gaze.LeftGazePoint2D.y)),
                self.acsd2pix((gaze.RightGazePoint2D.x,
                               gaze.RightGazePoint2D.y)))

    def getCurrentGazePosition(self):
        # returns the most recent gaze data point
        # format is ((left.x, left.y), (right.x, right.y))
        if len(self.gazeData) == 0:
            return (None, None, None, None)
        else:
            return self.getGazePosition(self.gazeData[-1])

    def getCurrentGazeAverage(self):
        # returns the most recent average gaze position
        # x and y
        if len(self.gazeData) == 0:
            return (None, None, None, None)
        else:
            lastGaze = self.gazeData[-1]
            if lastGaze.LeftValidity != 4 and lastGaze.RightValidity != 4:
                # return average data
                return self.acsd2pix((np.mean((lastGaze.LeftGazePoint2D.x,
                                               lastGaze.RightGazePoint2D.x)),
                                      np.mean((lastGaze.LeftGazePoint2D.y,
                                               lastGaze.RightGazePoint2D.y))))
            elif lastGaze.LeftValidity != 4 and lastGaze.RightValidity == 4:
                # only return left data
                return self.acsd2pix(lastGaze.LeftGazePoint2D.x,
                                     lastGaze.LeftGazePoint2D.y)
            elif lastGaze.LeftValidity == 4 and lastGaze.RightValidity != 4:
                # only return right data
                return self.acsd2pix(lastGaze.RightGazePoint2D.x,
                                     lastGaze.RightGazePoint2D.y)

    def getCurrentValidity(self):
        if len(self.gazeData) == 0:
            return (None, None, None, None)
        else:
            return (self.gazeData[-1].LeftValidity,
                    self.gazeData[-1].RightValidity)

    def waitForFixation(self, fixationPoint=(0, 0),
                        bothEyes=True, errorMargin=0.1):
        # this function waits until the eye tracker detects one (or both)
        # eyes to be at a certain point, +- some margin of error
        # fixation point should be given in pixels
        # first, make sure data is not saved:
        self.datafile_temp, self.datafile = self.datafile, None
        self.startTracking()  # kick off tracking
        psychopy.core.wait(0.5)  # allow the tracker to gather some data
        while (abs(self.getCurrentGazeAverage()[0] -
                   fixationPoint[0]) < errorMargin and
               abs(self.getCurrentGazeAverage()[1] -
                   fixationPoint[1]) < errorMargin and
               (not bothEyes or (self.getCurrentValidity()[0] != 4 and
                                 self.getCurrentValidity()[1] != 4))):
            psychopy.core.wait(0.05)  # wait 50ms before checking again
        self.stopTracking()  # stop tracking
        # then restore data file so tracking can continue
        self.datafile, self.datafile_temp = self.datafile_temp, None

    def getCurrentEyePosition(self):
        # returns the most recent eye position
        if len(self.gazeData) == 0:
            return((None, None, None), (None, None, None))
        else:
            self.gaze = self.gazeData[-1]
            return ((self.gaze.LeftEyePosition3D.x,
                     self.gaze.LeftEyePosition3D.y,
                     self.gaze.LeftEyePosition3D.z),
                    (self.gaze.RightEyePosition3D.x,
                     self.gaze.RightEyePosition3D.y,
                     self.gaze.RightEyePosition3D.z))

    def getCurrentPupilSize(self):
        if len(self.gazeData) == 0:
            return(none, none)
        else:
            return(self.gazeData[-1].LeftPupil,
                   self.gazeData[-1].RightPupil)

    def setDataFile(self, filename):
        if filename is None:
            self.datafile = None
        else:
            print 'set datafile ' + filename
            self.datafile = open(filename, 'w+')
            self.datafile.write('Recording date:\t' +
                                datetime.datetime.now().strftime('%Y/%m/%d') +
                                '\n')
            self.datafile.write('Recording time:\t' +
                                datetime.datetime.now().strftime('%H:%M:%S') +
                                '\n')
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
            print "Data file is not set, data not saved."
            return
        elif len(self.gazeData) == 0:
            print "No gazedata collected, no data saved."
            return

        print "Saving data."
        self.datafile.write(', '.join(['TimeStamp',
                                       'GazePointXLeft',
                                       'GazePointYLeft',
                                       'PupilLeft',
                                       'EyePositionXLeft',
                                       'EyePositionYLeft',
                                       'EyePositionZLeft',
                                       'ValidityLeft',
                                       'GazePointXRight',
                                       'GazePointYRight',
                                       'PupilRight',
                                       'EyePositionXRight',
                                       'EyePositionYRight',
                                       'EyePositionZRight',
                                       'ValidityRight',
                                       'Event']) + '\n')
        timeStampStart = self.gazeData[0].Timestamp  # first timepoint is 0s
        # Write eye info
        for g in self.gazeData:
            self.datafile.write(', '.join([
                '%.4f' % ((g.Timestamp - timeStampStart) / 1000.0),
                # Print the left eye data:
                '%.4f' % g.LeftGazePoint2D.x,
                '%.4f' % g.LeftGazePoint2D.y,
                '%.4f' % g.LeftPupil,
                '%.4f' % g.LeftEyePosition3D.x,
                '%.4f' % g.LeftEyePosition3D.y,
                '%.4f' % g.LeftEyePosition3D.z,
                '%d' % g.LeftValidity,
                # Print the right eye data:
                '%.4f' % g.RightGazePoint2D.x,
                '%.4f' % g.RightGazePoint2D.y,
                '%.4f' % g.RightPupil,
                '%.4f' % g.RightEyePosition3D.x,
                '%.4f' % g.RightEyePosition3D.y,
                '%.4f' % g.RightEyePosition3D.z,
                '%d' % g.RightValidity
            ]) + '\n')
        # Write the additional event data added
        for e in self.eventData:
            self.datafile.write(('%.4f' + ', ' * 14 + '%s\n') %
                                ((e[0] - timeStampStart) / 1000.0, e[1]))
        # flush the python data buffer (data written to file)
        self.datafile.flush()

    def setIllumination(self, mode):
        self.illuminationChanged = False
        self.eyetracker.SetIlluminationMode(mode,
                                            callback=self.on_illumchange)

    def on_illumchange(self, error, resp):
        if error:
            raise ValueError("Illumination Change didn't work.")
            print "on_illumchange: Error =", error
        self.illuminationChanged = True
        return False

    ########################################################################
    # helper functions
    ########################################################################

    def acsd2pix(self, xy):
        # Convert the tobii coordinates (acsd) to pixels
        # in tobii, (0, 0) is top left
        # in psychopy, (0, 0) is the middle
        return ((xy[0] - 0.5) * self.win.size[0],
                (0.5 - xy[1]) * self.win.size[1])

############################################################################
# run following codes if this file is executed directly
############################################################################

if __name__ == "__main__":
    import sys
    screen = psychopy.monitors.Monitor(name='tobiix300', width=51, distance=60)
    screen.setSizePix([1920, 1080])
    screen.setWidth(51)
    screen.setDistance(60)
    win = psychopy.visual.Window(fullscr=True, units='pix',
                                 monitor=screen, color=-1.0)
    controller = TobiiController(win)

    # check eye trackers and open the first one
    controller.waitForFindEyeTracker()
    controller.activate(controller.eyetrackers.keys()[0])

    # help the person find the eyes
    controller.findEyes()

    controller.setDataFile('testdata.csv')

    # Run the calibration routine
    while True:
        ret = controller.doCalibration(
            [(0.1, 0.1), (0.9, 0.1), (0.5, 0.5), (0.1, 0.9), (0.9, 0.9)])
        if ret == 'accept':
            break
        elif ret == 'abort':
            controller.destroy()
            raise KeyboardInterrupt("The calibration was aborted.")

    # Create a square that will move gaze contingently
    marker = psychopy.visual.Rect(win, width=20, height=20,
                                  fillColor=(1.0, 0.7, 0.7),
                                  units='pix',
                                  autoDraw=True)
    # Start tracking and update the position of the marker
    controller.startTracking()
    response = []
    while 'space' not in response:
        currentGazePosition = controller.getCurrentGazePosition()
        if None not in currentGazePosition:
            # set marker to arithmetic mean of the two gaze poisitions
            marker.pos = (np.mean((currentGazePosition[0][0],
                                   currentGazePosition[1][0])),
                          np.mean((currentGazePosition[0][1],
                                   currentGazePosition[1][1])))
        response = psychopy.event.getKeys()
        if 'w' in response:
            controller.recordEvent('w key')
        win.flip()

    controller.stopTracking()
    win.close()
    controller.closeDataFile()
    controller.destroy()
