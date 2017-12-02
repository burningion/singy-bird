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

if __name__ == '__main__':
    low_note, high_note = get_vocal_range()
    position_on_range()
