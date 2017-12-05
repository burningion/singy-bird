import aubio
import numpy as np
import pyaudio

import time
import argparse

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

q = queue.Queue()

def get_vocal_range(volume_thresh=0.01, cent_range=20, note_hold=20):

    note_curr = 0 # counter for how many consistent samples while recording
    range_low = "" # name of note we achieved at lowest range
    range_high = "" # name of note achieved at highest


    have_range = False

    previous_note = ""
    current_pitch = music21.pitch.Pitch()

    while True:

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

        current = current_pitch.nameWithOctave

        q.put({'Note': current, 'Cents': current_pitch.microtone.cents})
