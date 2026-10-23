"""Cut a 30s, beat-aligned hero score from a bMovies catalogue track.

usage: hero-score-catalogue.py <track.mp3> <track_bpm> <beat_phase_s> <A_start_bar> <A_beat_off> <B_bar> <out.wav>

Video grid: 120 BPM, beat k at 0.5*k s. End-card hit at 26.5s (beat 53).
Segment A  = track from bar A_start_bar (+A_beat_off beats) for 24.5s  (video 0 -> 24.5)
Segment B  = track from bar B_bar (1 bar before the track's own drop) for 5.5s (video 24.5 -> 30)
so the drop lands exactly on the end-card hit. Track is time-stretched to exactly 120 BPM.
A synthesized riser (24.5-26.5) and sub impact (26.5) sit under the track.
"""
import subprocess, sys, numpy as np, wave
track, bpm, phase, abar, aoff, bbar, out = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), int(sys.argv[4]), float(sys.argv[5]), int(sys.argv[6]), sys.argv[7]
sr = 44100
ratio = 120.0 / bpm  # atempo factor
beat = 60.0 / bpm
def seg(t0, dur):
    # t0/dur in source seconds; stretch to 120 BPM
    src_dur = dur / ratio
    cmd = ['ffmpeg', '-v', 'error', '-ss', f'{t0:.4f}', '-t', f'{src_dur:.4f}', '-i', track, '-ac', '2', '-ar', str(sr)]
    if abs(ratio - 1) > 1e-6: cmd += ['-af', f'atempo={ratio:.6f}']
    cmd += ['-f', 'f32le', '-']
    a = np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, '<f4').reshape(-1, 2).T.copy()
    n = int(dur * sr); a = a[:, :n]
    if a.shape[1] < n: a = np.pad(a, ((0, 0), (0, n - a.shape[1])))
    return a
barlen = 4 * beat
A = seg(phase + abar * barlen + aoff * beat, 24.5)
B = seg(phase + bbar * barlen, 5.5)
# B must carry the drop exactly 2.0s in; short crossfade at the splice
x = int(0.02 * sr)
fo = np.linspace(1, 0, x); fi = 1 - fo
A[:, -x:] *= fo; B[:, :x] *= 1  # B starts on the beat, keep its transient
N = int(30 * sr); y = np.zeros((2, N)); y[:, :A.shape[1]] += A; y[:, A.shape[1]:A.shape[1] + B.shape[1]] += B
y[:, A.shape[1] - x:A.shape[1]] += 0  # splice already faded A
rng = np.random.default_rng(11)
ref = np.sqrt(np.mean(y ** 2))
# riser 24.5 -> 26.5
r0, r1 = int(24.5 * sr), int(26.5 * sr); n = r1 - r0; tt = np.arange(n) / n
no = rng.standard_normal(n); no = no - np.convolve(no, np.ones(8) / 8, 'same')
ris = no * tt ** 2.4 * ref * 0.9
y[0, r0:r1] += ris; y[1, r0:r1] += ris[::-1] * 0.9
# impact at 26.5
n = int(1.4 * sr); t = np.arange(n) / sr
imp = np.sin(2 * np.pi * (34 * t + 60 / 7 * (1 - np.exp(-7 * t)))) * np.exp(-t * 2.8) * ref * 2.2
imp += rng.standard_normal(n) * np.exp(-t * 14) * ref * 0.8
i = int(26.5 * sr); y[:, i:i + n] += imp
# fades
f = int(0.012 * sr); y[:, :f] *= np.linspace(0, 1, f)
f = int(1.2 * sr); y[:, -f:] *= np.linspace(1, 0, f) ** 1.5
y = np.tanh(y * 0.9) / np.tanh(0.9)
y /= np.abs(y).max() * 1.02
w = wave.open(out, 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr)
w.writeframes((y.T * 32767).astype('<i2').tobytes()); w.close(); print('ok', out)
