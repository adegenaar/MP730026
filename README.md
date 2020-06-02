This repository is based on the https://github.com/baldengineer/dmm-ble-mp730026 project.

This project is Micro-Python based. The development was done using Windows 10/Visual Studio Code & the Pymakr extension and using a Sparkfun ESP32 Thing with an I2C connection to the ssd1306 based OLED.   

The inspiration and the initial code was based on the Bald Engineer's example code for the Multicomp Pro MP730026 DMM over BLE.

The MicroPython code is based on code from the following projects:
* The [uPyM5bLE](https://github.com/lemariva/uPyM5BLE/blob/master/ble_examples/ble_temperature.py) MicroPython example code for the basic structure of the BLE scanner
* The [BLE-mp730026](https://github.com/baldengineer/dmm-ble-mp730026) example code from James Lewis AKA "The Bald Engineer"
* The [Font-To-Py](https://github.com/peterhinch/micropython-font-to-py) project from Peter Hinch to use arbitrary fonts on the OLED screen


Future plans:
* Seperate the BLE code from the display and packet decoding, perhaps a "Meter" base class and a sub-classed version for the MP730026
* Separate platform specific code so that the Python and MicroPython implementations can share as much code as possible
* Test a version under circuit-python  