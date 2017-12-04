from voiceController import get_vocal_range, position_on_range, q, stream

from threading import Thread

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

    pipeVelX = -2


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
        if 0 < upperPipes[0]['x'] < 4:
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

min_note, max_note = get_vocal_range()
t = Thread(target=position_on_range, args=(min_note, max_note))
t.daemon = True
t.start()

draw_pygame()
stream.stop_stream()
stream.close()
pygame.display.quit()

