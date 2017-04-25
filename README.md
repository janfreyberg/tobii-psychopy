# tobii psychopy
This is a port, with some modifications, of a script written by @SogoHiroyuki, to make it easier to use tobiis from psychopy.

The original is located here:
http://www.s12600.net/psy/etc/python.html#TobiiController

I have taken the Psychopy version of his script and adapted it to:
- not use PIL
- have a slightly more intuitive calibration procedure

### Installation
Install by typing: pip install git+https://github.com/janfreyberg/tobii-psychopy.git

#### Dependencies
You will need:
- numpy (`pip install numpy`)
- psychopy (`pip install psychopy`, but check the requirements at [psychopy.org](www.psychopy.org)
- the tobii pro analytics sdk 3.X ([from the tobii website](http://www.tobiipro.com/product-listing/tobii-pro-analytics-sdk/))
- datetime (`pip install datetime`)

### Usage
You can try out the controller by running tobiicontroller.py as a script rather than importing it: enter `python tobiicontroller.py` in a commandline in the same directory as the file.

When using it as part of a PsychoPy experiment, import it first, and then create a "controller" class by calling `myController = tobiicontroller.TobiiController(window)`, where `window` is the handle of an open psychopy window.

The following functions of the controller can be used for calibrating and tracking:

- `myController.findEyes()` mirrors the eyes so you can adjust the angle of the tobii and move the participant to the right distance
- `myController.doCalibration()` calibrates the scanner. You can provide, as an optional argument, a list of tuples that contain the coordinates of your points. You should provide this list in "Active Display Coordinates", where `(0.0, 0.0)` is top left, and `(1.0, 1.0)` is bottom right. The default is `[(0.5, 0.5), (0.1, 0.9), (0.1, 0.1), (0.9, 0.9), (0.9, 0.1)]`, and more or fewer points aren't really advisable.
- `myController.setDataFile(filename)` for setting where to save data. Currently, this overwrites whatever is in the file before, so make sure you set a new file for each trial you do. You can provide `None` if you don't want data to be saved.
- `myController.startTracking()` and `myController.stopTracking()` for tracking. This means the tobii actually produces data that gets picked up by python.
- `myController.recordEvent(eventString)` if you want to record something that happened. This makes sure you have a record of events - i.e. stimulus onset - that is synchronised to the tobii eye tracking data stream.
- `myController.getCurrentGazePosition()`, `myController.getCurrentGazeAverage`, `myController.getCurrentPupilSize`, `myController.getCurrentEyePosition`, if you want to get online estimates of where the subject is looking, what the pupil size is, and where the eyes are in 3D space, respectively.
