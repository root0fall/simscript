''' Joystick abstraction layer '''

from ctypes import CDLL, Structure, byref, c_void_p, c_char_p, c_long, c_bool, c_ubyte, c_short, c_byte
import logging,traceback,os.path

class Joystick:
    
    def __init__(self, joysticks, nameOrIndex):
        
        if isinstance(nameOrIndex, int):
            if nameOrIndex < joysticks.numJoysticks():
                index = nameOrIndex
        else: 
            for j in range(0, joysticks.numJoysticks()) :
                if nameOrIndex == str(Joysticks._sdl.SDL_JoystickName(j), "utf-8"):
                    index = j

        try:    
            self.index = index;
        except:
            raise EnvironmentError("joysticks.get('%s') is not available" % nameOrIndex)

        self._handle = c_void_p()
        self.name = str(Joysticks._sdl.SDL_JoystickName(self.index), "utf-8")
        
    def _acquire(self):
        if self._handle:
            return
        self._handle = Joysticks._sdl.SDL_JoystickOpen(self.index)
        if not self._handle:
            raise EnvironmentError("joysticks.get('%s') can't be acquired" % self.index)
            
        
    def numAxis(self):
        return Joysticks._sdl.SDL_JoystickNumAxes(self._handle) if self._handle else 0

    def getAxis(self, i):
        return Joysticks._sdl.SDL_JoystickGetAxis(self._handle, i) / 32767  if self._handle else 0
    
    def numButtons(self):
        return Joysticks._sdl.SDL_JoystickNumButtons(self._handle)  if self._handle else 0
    
    def getButton(self, i):
        return Joysticks._sdl.SDL_JoystickGetButton(self._handle, i)  if self._handle else False
    
    def __str__(self):
        # button/axis information isn't available before acquired
        return "joysticks.get('%s') # index %d" % (self.name, self.index)
    

class VirtualJoystick:
    
    NAME = 'vJoy Device'

    _VJD_STAT_OWN  = 0 # Device is owned by this application.
    _VJD_STAT_FREE = 1 # Device is NOT owned by any application (including this one).
    _VJD_STAT_BUSY = 2 # Device is owned by another application. It cannot be acquired by this application.
    _VJD_STAT_MISS = 3 # Device is missing. It either does not exist or the driver is down.
    _VJD_STAT_UNKN = 4 # Unknown

    _HID_USAGE_X  = 0x30
    _HID_USAGE_Y  = 0x31
    _HID_USAGE_Z  = 0x32
    _HID_USAGE_RX  = 0x33
    _HID_USAGE_RY  = 0x34
    _HID_USAGE_RZ  = 0x35
    _HID_USAGE_SL0 = 0x36
    _HID_USAGE_SL1 = 0x37
    _HID_USAGE_WHL = 0x38
    
    _axisKeys = [_HID_USAGE_X, _HID_USAGE_Y, _HID_USAGE_Z, _HID_USAGE_RX, _HID_USAGE_RY, _HID_USAGE_RZ, _HID_USAGE_SL0, _HID_USAGE_SL1, _HID_USAGE_WHL]
    

    class Position(Structure):
        _fields_ = [
          ("index", c_byte),
          ("wThrottle", c_long),
          ("wRudder", c_long),
          ("wAileron", c_long),
          ("wAxisX", c_long),
          ("wAxisY", c_long),
          ("wAxisZ", c_long),
          ("wAxisXRot", c_long), 
          ("wAxisYRot", c_long),
          ("wAxisZRot", c_long),
          ("wSlider", c_long),
          ("wDial", c_long),
          ("wWheel", c_long),
          ("wAxisVX", c_long),
          ("wAxisVY", c_long),
          ("wAxisVZ", c_long),
          ("wAxisVBRX", c_long), 
          ("wAxisVBRY", c_long),
          ("wAxisVBRZ", c_long),
          ("lButtons", c_long),  # 32 buttons: 0x00000001 to 0x80000000 
          ("bHats", c_long),     # Lower 4 bits: HAT switch or 16-bit of continuous HAT switch
          ("bHatsEx1", c_long),  # Lower 4 bits: HAT switch or 16-bit of continuous HAT switch
          ("bHatsEx2", c_long),  # Lower 4 bits: HAT switch or 16-bit of continuous HAT switch
          ("bHatsEx3", c_long)   # Lower 4 bits: HAT switch or 16-bit of continuous HAT switch
          ]
    

    def __init__(self, joysticks, joystick, virtualIndex):
        self.index = joystick.index
        self.name = joystick.name
        
        self._position = VirtualJoystick.Position()
        self._position.index = virtualIndex+1
        
        self._acquired = False

        self._buttons = Joysticks._vjoy.GetVJDButtonNumber(self._position.index)
        
        self._axis = []
        for akey in VirtualJoystick._axisKeys:
            if Joysticks._vjoy.GetVJDAxisExist(self._position.index, akey):
                amax = c_long()
                amin = c_long()
                Joysticks._vjoy.GetVJDAxisMin(self._position.index, akey, byref(amin))
                Joysticks._vjoy.GetVJDAxisMax(self._position.index, akey, byref(amax))
                self._axis.append((akey, amin.value,amax.value)) 
                
    def _acquire(self):
        if self._acquired:
            return
        if not Joysticks._vjoy.AcquireVJD(self._position.index):
            raise EnvironmentError("joysticks.get('%s') is not a free Virtual Joystick" % self.index)
        self._acquired = True
                
    def numAxis(self):
        return len(self._axis)

    def getAxis(self, i):
        if i<0 or i>=len(self._axis):
            raise EnvironmentError("joysticks.get('%s') doesn't have axis %d" % i)
        return self._axis[i]._aval
    
    def setAxis(self, a, value):
        if a<0 or a>=len(self._axis):
            raise EnvironmentError("joysticks.get('%s') doesn't have axis %d" % a)
        akey, amin, amax = self._axis[a]
        if value < amin or value > amax:
            raise EnvironmentError("joysticks.get('%s') value for axis %d not %d > %d > %d" % (self.index, a, amin, value, amax))
        '''
        if not Joysticks._vjoy.SetAxis(value, self._virtualIndex+1, axis._akey):
            raise EnvironmentError("joysticks.get('%s') axis %d can't be set to %d" % (self.index, a, value))
        '''
        
    
    def numButtons(self):
        return len(self._buttons)
    
    def getButton(self, i):
        if i<0 or i>=len(self._buttons):
            raise EnvironmentError("joysticks.get('%s') doesn't have button  %d" % i)
        return self._buttons[i]
    
    def setButton(self, i, value):

        self._position.wAxisX = 30000
        self._position.__setattr__('wAxisY', 30000) 
        self._position.lButtons = 2
        if not Joysticks._vjoy.UpdateVJD(self._position.index, byref(self._position)):
            raise EnvironmentError("joysticks.get('%s') button %d can't be set to %d" % (self.index, i, value))

        '''        
        if i<0 or i>=len(self._buttons):
            raise EnvironmentError("joysticks.get('%s') doesn't have button  %d" % i)
        if not Joysticks._vjoy.SetBtn(c_bool(value), c_short(self._virtualIndex+1), c_ubyte(i+1)):
            raise EnvironmentError("joysticks.get('%s') button %d can't be set to %d" % (self._virtualIndex, i, value))
        self._buttons[i] = value
        '''
        return True
    
    def __str__(self):
        return "joysticks.get('%s') # VirtualJoystick index %d" % (self.name, self.index)
    
    
class Joysticks: 

    _log = logging.getLogger(__name__)
    _sdl = None
    _vjoy = None
            
    def __init__(self):
        
        joysticks = []
        
        # preload all available joysticks for reporting
        if not Joysticks._sdl: 
            try:
                Joysticks._sdl = CDLL(os.path.join("contrib","sdl","SDL.dll"))
                Joysticks._sdl.SDL_Init(0x200)
                Joysticks._sdl.SDL_JoystickName.restype = c_char_p
                for index in range(0, Joysticks._sdl.SDL_NumJoysticks()) :
                    joy = Joystick(self, index)
                    joysticks.append(joy)
            except Exception:
                Joysticks._log.warning("Cannot initialize support for physical Joysticks")
                Joysticks._log.debug(traceback.format_exc())

        # wrap virtual joysticks where applicable                
        if not Joysticks._vjoy: 
            try:
                Joysticks._vjoy = CDLL(os.path.join("contrib", "vjoy", "vJoyInterface.dll"))
                
                if not Joysticks._vjoy.vJoyEnabled():
                    Joysticks._log.info("No Virtual Joystick Driver active")
                    return

                numVirtuals = 0
                                
                for i,joy in enumerate(joysticks):
                    if joy.name == VirtualJoystick.NAME:
                        try:
                            virtual = VirtualJoystick(self, joy, numVirtuals)
                            joysticks[i] = virtual
                        except:
                            Joysticks._log.warning("Cannot initialize support for virtual Joystick %s" % joy.name)
                            Joysticks._log.warning(traceback.format_exc())
                        numVirtuals += 1
                    
            except Exception:
                Joysticks._log.warning("Cannot initialize support for virtual Joysticks")
                Joysticks._log.warning(traceback.format_exc())

        # build dictionary
        self._joysticks = dict()
        for joy in joysticks:
            self._joysticks[joy.name] = joy 
            self._joysticks[joy.index] = joy 
            Joysticks._log.info(joy)

                
    def numJoysticks(self):
        return Joysticks._sdl.SDL_NumJoysticks() if Joysticks._sdl else 0
    
    def get(self,nameOrIndex):
        try:
            joy = self._joysticks[nameOrIndex]
        except:
            joy = Joystick(self, nameOrIndex)
            self._joysticks[joy.index] = joy
            self._joysticks[joy.name] = joy 
        joy._acquire()
        return joy
    
    
    def button(self, nameOrIndexAndButton):
        """ test button eg button 1 of Saitek Pro Flight Quadrant via button('Saitek Pro Flight Quadrant.1') """
        nameOrIndex, button = nameOrIndexAndButton.split(".")
        return self.get(nameOrIndex).button(int(button))
        
    def poll(self):
        if not Joysticks._sdl:
            return
        # poll
        Joysticks._sdl.SDL_JoystickUpdate()
    
def init():
    return Joysticks()
