# Desktop Virtual Pet

A small, frameless PyQt6 pet that stays above other windows and uses the four
transparent pixel-art sprites in this folder.

## Run

```powershell
python -m pip install -r requirements.txt
python main.py
```

Right-click the pet to Feed, Play, Sleep/Wake, view Status, or Exit. Drag it
with the left mouse button. Hover over it to display its stats. The pet's
hunger, happiness, and energy change over time; it wanders along the bottom of
the screen while awake.

## Sprite moods

- `normal.png`: default content expression
- `angry.png`: hunger is low
- `sad.png`: happiness is low
- `sleepy.png`: the pet is sleeping or energy is low
