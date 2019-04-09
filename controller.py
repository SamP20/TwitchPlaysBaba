from input import press_once
import time

DIRECTIONS = {
    'u': 0x11,
    'd': 0x1f,
    'l': 0x1e,
    'r': 0x20,
    's': 0x39
}

def movement(dirs):
    for d in dirs:
        press_once(DIRECTIONS[d])

def back_to_map():
    press_once(0x01) #esc
    press_once(0x1f) #down
    press_once(0x1c) #enter
    press_once(0x01) #esc in case we're at main map

def restart():
    # R key
    press_once(0x13)

def wait_for_map():
    time.sleep(8.0)


if __name__ == "__main__":
    time.sleep(4.0)
    movement('s')
    wait_for_map()
    movement('d'*8) # compelte 1st level
    wait_for_map()
    movement('dww') 
    movement('s') # go to 2nd level
    wait_for_map()
    movement('waaadwwwwwwwwwassssdsaaaddddddwwwassdsaaaaad') # compelte 2nd level
    wait_for_map()

    #repeat('d', 7)