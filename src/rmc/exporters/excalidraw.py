"""Convert blocks to svg file.

Code originally from https://github.com/lschwetlick/maxio through
https://github.com/chemag/maxio .
"""

import logging
import string
import random
import json
import time
import dataclasses

from typing import Iterable

from rmscene import (

    Block,
    RootTextBlock,
    SceneLineItemBlock,
    AuthorIdsBlock,
    MigrationInfoBlock,
    PageInfoBlock,
    SceneTreeBlock,
    TreeNodeBlock,
    SceneGroupItemBlock
)

_logger = logging.getLogger(__name__)

SCREEN_WIDTH = 1404
SCREEN_HEIGHT = 1872
XPOS_SHIFT = SCREEN_WIDTH / 2

@dataclasses.dataclass()
class ExcalidrawDocument:
    type: str = "excalidraw"
    version: int = 2
    source: str = "excalidraw.py"
    elements: list = dataclasses.field(default_factory=list)
    appState: dict = dataclasses.field(default_factory=lambda: {
            'gridSize': None,
            'viewBackgroundColor': '#ffffff'
        })
    files: dict = dataclasses.field(default_factory=lambda: {})

def randomId():
    return ''.join(random.choice(string.ascii_letters+string.digits+"-_") for i in range(21)) #Nanoid 

def randomInt():
    return random.randint(0, 1024)

def randomNonce():
    return round(random.random() * 2 ** 31)

def timestampInMiliseconds():
    return round(time.time()*1000)

@dataclasses.dataclass()
class ExcalidrawElement:
    x: int = 0
    y: int = 0
    
    width: int = 0
    height: int = 0
    
    frameId: str = None

    id: str = dataclasses.field(default_factory=randomId)    
    version: int = dataclasses.field(default_factory=randomInt)
    seed: int = dataclasses.field(default_factory=randomNonce)
    updated: int = dataclasses.field(default_factory=timestampInMiliseconds)
    versionNonce: int = dataclasses.field(default_factory=randomNonce)
    
    angle: float = 0
    roughness: int = 1
    opacity: int = 100
    
    strokeWidth: int = 1
    strokeStyle: str = "solid"
    strokeColor: str = "#000000"
    backgroundColor: str = "transparent"
    fillStyle: str = "hachure"
    
    groupIds: list = dataclasses.field(default_factory=list)
    
    roundness: str = None
    
    isDeleted: bool = False
    link: str = None
    locked: bool = False
    boundElements: str = None
    containerId: str = None

# Following name convention:
# https://github.com/excalidraw/excalidraw/blob/master/src/element/types.ts#L134
@dataclasses.dataclass(kw_only=True)
class ExcalidrawTextElement(ExcalidrawElement):
    type: str = "text"
    
    text: str
    originalText: str #Copy of text?

    fontSize: int = 20 #Medium
    lineHeight: float = 1.25
    fontFamily: int = 1
    
    textAlign: str = "left"
    verticalAlign: str = "top"
    baseline: int = 18

@dataclasses.dataclass(kw_only=True)
class ExcalidrawFreedrawElement(ExcalidrawElement):
    type: str = "freedraw"
    
    points: list = dataclasses.field(default_factory=list)
    lastCommittedPoint: list = None
    pressures: list = dataclasses.field(default_factory=list)
    simulatePressure: bool = True


class DataclassJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        return super().default(o)

def blocks_to_excalidraw(blocks: Iterable[Block])-> ExcalidrawDocument:
    """Convert Blocks to Excalidraw."""
    
    document = ExcalidrawDocument()
    version = random.randint(1, 50)
    
    for block in blocks:
        version = version+1
        if isinstance(block, SceneLineItemBlock):
            _logger.warning('SceneLineItemBlock')
            excalidrawElement = draw_stroke(block)            
        elif isinstance(block, RootTextBlock):
            _logger.warning('RootTextBlock')
            excalidrawElement = draw_text(block)
        else:
            _logger.warning('warning: not converting block: %s', block.__class__)
            continue
            
        excalidrawElement.version = version
        document.elements.append(excalidrawElement)
        
    return document

def excalidrawDocument_to_str(document: ExcalidrawDocument) -> str:
    return json.dumps(document, cls=DataclassJSONEncoder, indent=4)

def blocks_to_excalidraw_str(blocks: Iterable[Block]) -> str:
    return excalidrawDocument_to_str(blocks_to_excalidraw(blocks))

def draw_stroke(block) -> ExcalidrawFreedrawElement:
    _logger.debug('Processing: SceneLineItemBlock')
    # make sure the object is not empty

    excalidrawStroke = ExcalidrawFreedrawElement()
    if block.item.value is None:
        return excalidrawStroke

    absolutePoints = []
    pressures = []
    for _ , point in enumerate(block.item.value.points):
        x = point.x 
        y = point.y 
        absolutePoints.append([x,y])
        pressures.append(point.pressure)
        #print(point.speed, point.direction, point.width, point.pressure)

    excalidrawStroke.x = absolutePoints[0][0]
    excalidrawStroke.y = absolutePoints[0][1]
    
    relativePoints = []
    for ap in absolutePoints:
        x = ap[0] - excalidrawStroke.x
        y = ap[1] - excalidrawStroke.y
        relativePoints.append([x,y])

    excalidrawStroke.points = relativePoints
    excalidrawStroke.pressures = pressures
    return excalidrawStroke


def draw_text(block) -> ExcalidrawTextElement:
    # Excalidraw doesnt support bold / italic, skipping the textformattig
    _logger.debug('Processing: RootTextBlock')

    text = "".join([i[1] for i in block.value.items.items()])
    
    x = block.value.pos_x + XPOS_SHIFT
    y = block.value.pos_y
    width = round(block.value.width)
    # To get line height in px, multiply with font size. Multiply by number of lines
    # https://github.com/excalidraw/excalidraw/blob/master/src/element/types.ts#L161
    height = ExcalidrawTextElement.fontSize * ExcalidrawTextElement.lineHeight * len(text.splitlines()) 
    
    excalidrawText = ExcalidrawTextElement(x=round(x), 
                                            y=round(y),
                                            width=round(width),
                                            height=round(height),
                                            text=text,
                                            originalText=text)
    return excalidrawText

