import aubio
import numpy as np
import pyaudio

import time
import argparse

from threading import Thread
import queue

import music21 # yes!

parser = argparse.ArgumentParser()
parser.add_argument("-input", required=False, type=int, help="Audio Input Device")
args = parser.parse_args()

if not args.input:
    print("No input device specified. Printing list of input devices now: ")
    p = pyaudio.PyAudio()
    for i in range(p.get_device_count()):
        print("Device number (%i): %s" % (i, p.get_device_info_by_index(i).get('name')))
    print("Run this program with -input 1, or the number of the input you'd like to use.")
    exit()

# PyAudio object.
p = pyaudio.PyAudio()

# Open stream.
stream = p.open(format=pyaudio.paFloat32,
                channels=1, rate=44100, input=True,
                input_device_index=args.input, frames_per_buffer=4096)
time.sleep(1)
# Aubio's pitch detection.
pDetection = aubio.pitch("default", 2048,
    2048//2, 44100)
# Set unit.
pDetection.set_unit("Hz")
pDetection.set_silence(-40)

def get_vocal_range(volume_thresh=0.01, cent_range=20, note_hold=20):

    note_curr = 0 # counter for how many consistent samples while recording
    range_low = "" # name of note we achieved at lowest range
    range_high = "" # name of note achieved at highest


    have_range = False

    previous_note = ""
    current_pitch = music21.pitch.Pitch()

    while not have_range:

        data = stream.read(1024, exception_on_overflow=False)
        samples = np.fromstring(data,
                                dtype=aubio.float_type)
        pitch = pDetection(samples)[0]

        # Compute the energy (volume) of the
        # current frame.
        volume = np.sum(samples**2)/len(samples) * 100
        #print(volume)

        if pitch and volume > volume_thresh: # adjust with your mic! .0002 if for my telecaster, .001 for my mic
            current_pitch.frequency = pitch
        else:
            continue

        if current_pitch.microtone.cents > cent_range:
            print("Note %s outside of Cent Range with %i" %
                  (current_pitch.nameWithOctave, current_pitch.microtone.cents))
            previous_note = ""
            continue

        current = current_pitch.nameWithOctave

        
        if current == previous_note:
            note_curr += 1
            if note_curr == note_hold:
                if range_low != "" and range_low != current:
                    range_high = current
                    have_range = True
                    print("got range of high")
                else:
                    range_low = current
                    print("got range of low")
        else:
            note_curr = 0
            note = current
            previous_note = current
            print(current)

    return range_low, range_high

min_note, max_note = get_vocal_range()
print("total range: %s to %s" % (min_note, max_note))

q = queue.Queue()

def position_on_range(low_note, high_note, volume_thresh=.001, cent_range=3):
    lowNote = music21.note.Note(low_note)
    highNote = music21.note.Note(high_note)

    vocalInterval = music21.interval.notesToInterval(lowNote, highNote)

    current_pitch = music21.pitch.Pitch()

    while True:

        data = stream.read(1024, exception_on_overflow=False)
        samples = np.fromstring(data,
                                dtype=aubio.float_type)
        pitch = pDetection(samples)[0]

        # Compute the energy (volume) of the
        # current frame.
        volume = np.sum(samples**2)/len(samples)

        if pitch and volume > volume_thresh: # adjust with your mic! .0002 if for my telecaster, .001 for my mic
            current_pitch.frequency = pitch
        else:
            continue

        if current_pitch.microtone.cents > cent_range:
            #print("Outside of Cent Range with %i" % current_pitch.microtone.cents)
            continue

        current = current_pitch.nameWithOctave

        cur_interval = music21.interval.notesToInterval(lowNote, current_pitch)
        q.put(cur_interval.cents / vocalInterval.cents)

import pygame
import random
from itertools import cycle

PIPEGAPSIZE = 100
screenWidth, screenHeight = 288, 512
screen = pygame.display.set_mode((screenWidth, screenHeight)) 

clock = pygame.time.Clock()

bird = ('images/redbird-downflap.png',
        'images/redbird-midflap.png',
        'images/redbird-upflap.png')

background = 'images/background-day.png'
pipe = 'images/pipe-green.png'

IMAGES = {}
HITMASKS = {}
IMAGES['background'] = pygame.image.load(background).convert()
IMAGES['player'] = (
    pygame.image.load(bird[0]).convert_alpha(),
    pygame.image.load(bird[1]).convert_alpha(),
    pygame.image.load(bird[2]).convert_alpha(),
)

IMAGES['pipe'] = (
    pygame.transform.flip(
        pygame.image.load(pipe).convert_alpha(), False, True),
    pygame.image.load(pipe)
)

IMAGES['base'] = pygame.image.load('images/base.png').convert_alpha()
BASEY = screenHeight * 0.89

def checkCrash(player, upperPipes, lowerPipes):
    """returns True if player collders with base or pipes."""
    pi = player['index']
    player['w'] = IMAGES['player'][0].get_width()
    player['h'] = IMAGES['player'][0].get_height()

    # if player crashes into ground
    if player['y'] + player['h'] >= BASEY - 1:
        return [True, True]
    else:

        playerRect = pygame.Rect(player['x'], player['y'],
                      player['w'], player['h'])
        pipeW = IMAGES['pipe'][0].get_width()
        pipeH = IMAGES['pipe'][0].get_height()

        for uPipe, lPipe in zip(upperPipes, lowerPipes):
            # upper and lower pipe rects
            uPipeRect = pygame.Rect(uPipe['x'], uPipe['y'], pipeW, pipeH)
            lPipeRect = pygame.Rect(lPipe['x'], lPipe['y'], pipeW, pipeH)

            # player and upper/lower pipe hitmasks
            pHitMask = HITMASKS['player'][pi]
            uHitmask = HITMASKS['pipe'][0]
            lHitmask = HITMASKS['pipe'][1]

            # if bird collided with upipe or lpipe
            uCollide = pixelCollision(playerRect, uPipeRect, pHitMask, uHitmask)
            lCollide = pixelCollision(playerRect, lPipeRect, pHitMask, lHitmask)

            if uCollide or lCollide:
                return [True, False]

    return [False, False]

def pixelCollision(rect1, rect2, hitmask1, hitmask2):
    """Checks if two objects collide and not just their rects"""
    rect = rect1.clip(rect2)

    if rect.width == 0 or rect.height == 0:
        return False

    x1, y1 = rect.x - rect1.x, rect.y - rect1.y
    x2, y2 = rect.x - rect2.x, rect.y - rect2.y

    for x in range(rect.width):
        for y in range(rect.height):
            if hitmask1[x1+x][y1+y] and hitmask2[x2+x][y2+y]:
                return True
    return False

def getHitmask(image):
    """returns a hitmask using an image's alpha."""
    mask = []
    for x in range(image.get_width()):
        mask.append([])
        for y in range(image.get_height()):
            mask[x].append(bool(image.get_at((x,y))[3]))
    return mask

def getRandomPipe():
    """returns a randomly generated pipe"""
    # y of gap between upper and lower pipe
    gapY = random.randrange(0, int(BASEY * 0.6 - PIPEGAPSIZE))
    gapY += int(BASEY * 0.2)
    pipeHeight = IMAGES['pipe'][0].get_height()
    pipeX = screenWidth + 10

    return [
        {'x': pipeX, 'y': gapY - pipeHeight},  # upper pipe
        {'x': pipeX, 'y': gapY + PIPEGAPSIZE}, # lower pipe
    ]

# hismask for pipes
HITMASKS['pipe'] = (
    getHitmask(IMAGES['pipe'][0]),
    getHitmask(IMAGES['pipe'][1]),
)

# hitmask for player
HITMASKS['player'] = (
    getHitmask(IMAGES['player'][0]),
    getHitmask(IMAGES['player'][1]),
    getHitmask(IMAGES['player'][2]),
)

def draw_pygame():
    running = True
    playerIndex = 0
    playerIndexGen = cycle([0, 1, 2, 1])
    # iterator used to change playerIndex after every 5th iteration
    loopIter = 0

    basex = 0
    # amount by which base can maximum shift to left
    baseShift = IMAGES['base'].get_width() - IMAGES['background'].get_width()

    playerX = int(screenWidth * .2)
    playerY = screenHeight // 2

    basex = 0
    baseShift = IMAGES['base'].get_width() - IMAGES['background'].get_width()

    # get 2 new pipes to add to upperPipes lowerPipes list
    newPipe1 = getRandomPipe()
    newPipe2 = getRandomPipe()

    # list of upper pipes
    upperPipes = [
        {'x': screenWidth + 200, 'y': newPipe1[0]['y']},
        {'x': screenWidth + 200 + (screenWidth / 2), 'y': newPipe2[0]['y']},
    ]

    # list of lowerpipe
    lowerPipes = [
        {'x': screenWidth + 200, 'y': newPipe1[1]['y']},
        {'x': screenWidth + 200 + (screenWidth / 2), 'y': newPipe2[1]['y']},
    ]

    pipeVelX = -4


    while running:
        key = pygame.key.get_pressed()
        if key[pygame.K_q]:
            running = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        screen.fill((0,0,0))

        if not q.empty():
            b = q.get()
            if b > 0 and b < 1:
               playerY = screenHeight - int(screenHeight * b) 
        else:
            playerY = playerY + 2

        crashTest = checkCrash({'x': playerX, 'y': playerY, 'index': playerIndex},
                               upperPipes, lowerPipes)

        for pipe in upperPipes:
            pipeMidPos = pipe['x'] + IMAGES['pipe'][0].get_width() / 2

        # move pipes to left
        for uPipe, lPipe in zip(upperPipes, lowerPipes):
            uPipe['x'] += pipeVelX
            lPipe['x'] += pipeVelX

        # add new pipe when first pipe is about to touch left of screen
        if 0 < upperPipes[0]['x'] < 5:
            newPipe = getRandomPipe()
            upperPipes.append(newPipe[0])
            lowerPipes.append(newPipe[1])

        # remove first pipe if its out of the screen
        if upperPipes[0]['x'] < -IMAGES['pipe'][0].get_width():
            upperPipes.pop(0)
            lowerPipes.pop(0)

        screen.blit(IMAGES['background'], (0,0))

        for uPipe, lPipe in zip(upperPipes, lowerPipes):
            screen.blit(IMAGES['pipe'][0], (uPipe['x'], uPipe['y']))
            screen.blit(IMAGES['pipe'][1], (lPipe['x'], lPipe['y']))

        if (loopIter + 1) % 5 == 0:
            playerIndex = next(playerIndexGen)
        loopIter = (loopIter + 1) % 30
        basex = -((-basex + 4) % baseShift)

        screen.blit(IMAGES['base'], (basex, BASEY))
        screen.blit(IMAGES['player'][playerIndex],
                    (playerX, playerY))
        
        pygame.display.flip()
        clock.tick(60)

t = Thread(target=position_on_range, args=(min_note, max_note))
t.daemon = True
t.start()

draw_pygame()
stream.stop_stream()
stream.close()
pygame.display.quit()

