"""Mixed-script text measurement and unit-safe line breaking for native PPT text."""
from functools import lru_cache
from pathlib import Path
import os,re,unicodedata

EAST_ASIAN='Microsoft YaHei'
LATIN='Times New Roman'

@lru_cache(maxsize=48)
def _fonts(size,bold=False):
    from PIL import ImageFont
    folder=Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts'
    ea=folder/('msyhbd.ttc' if bold else 'msyh.ttc')
    latin=folder/('timesbd.ttf' if bold else 'times.ttf')
    if not ea.is_file() or not latin.is_file():return None
    # Measure at 4x to reduce integer-font rounding; values remain CSS px.
    return ImageFont.truetype(str(ea),round(size*4)),ImageFont.truetype(str(latin),round(size*4))

def measure(text,size,bold=False):
    fonts=_fonts(size,bold)
    if fonts is None:
        return sum(size*(1.04 if unicodedata.east_asian_width(c) in 'WF' else .65) for c in text)
    total=0.;current='';last=None
    for char in text:
        index=0 if unicodedata.east_asian_width(char) in 'WF' else 1
        if index!=last and current:total+=fonts[last].getlength(current)/4;current=''
        current+=char;last=index
    if current:total+=fonts[last].getlength(current)/4
    return total

def wrap(text,width,size,bold=False):
    """Do not split numerical quantities from their units or orphan punctuation."""
    text=str(text)
    text=re.sub(r'\b(Mg|Ca)2\+',lambda m:m.group(1)+'²⁺',text)
    text=re.sub(r'\b(Na|K)\+',lambda m:m.group(1)+'⁺',text)
    text=re.sub(r'\bCO2\b','CO₂',text)
    lines=[];available=max(10,width-10)
    unit=r'(?:μM|µM|mM|nM|pM|M|μL|µL|mL|nm|μm|µm|mm|ms|s|min|h|kDa|Å|%|°C)'
    pattern=r'\d+(?:\.\d+)?\s*'+unit+r'|[A-Za-z][A-Za-z0-9_./+−–-]*|\d+(?:\.\d+)?|\s+|.'
    for para in text.split('\n'):
        paragraph_start=len(lines)
        row=''
        for token in re.findall(pattern,para):
            numeric=bool(re.fullmatch(r'\d+(?:\.\d+)?(?:\s*'+unit+r')?',token))
            if row and measure(row+token,size,bold)>available:
                if token in '，。；：、！？）》】,.!?;:':
                    tail=re.search(r'(?:\d+(?:\.\d+)?(?:\s*'+unit+r')?|[A-Za-z][A-Za-z0-9_./+−–-]*|.)$',row).group(0)
                    rest=row[:-len(tail)]
                    if rest:lines.append(rest.rstrip());row=tail
                    elif measure(row+token,size,bold)>width:
                        raise ValueError('TEXT_ATOM_NEEDS_WIDER_BOX: '+row+token)
                else:lines.append(row.rstrip());row=''
            if measure(token,size,bold)>available and not numeric:
                for c in token:
                    if row and measure(row+c,size,bold)>available:lines.append(row.rstrip());row=''
                    row+=c
            else:row+=token
        lines.append(row.rstrip())
        # Avoid a final orphan such as "介。" while preserving every character
        # and without splitting a numerical quantity or Latin identifier.
        if len(lines)-paragraph_start>=2 and re.fullmatch(r'[\u3400-\u9fff，。；：！？]{1,3}',lines[-1]):
            tail=re.search(r'[\u3400-\u9fff，。；：、！？]{2,4}$',lines[-2])
            if tail and measure(tail.group(0)+lines[-1],size,bold)<=available:
                lines[-2]=lines[-2][:-len(tail.group(0))];lines[-1]=tail.group(0)+lines[-1]
    return '\n'.join(lines)
