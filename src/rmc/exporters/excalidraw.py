"""Convert blocks to Excalidraw file."""

import logging
import string
import random
import hashlib
import json
import time
import dataclasses
from enum import Enum
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
from rmscene.scene_items import Pen

_logger = logging.getLogger(__name__)

SCREEN_WIDTH = 1404
SCREEN_HEIGHT = 1872
XPOS_SHIFT = SCREEN_WIDTH / 2

# Based Hexcodes based on the HTML Colornames
class HexPenColors(Enum):
    
    BLACK = "#000000"
    WHITE = "#FFFFFF"
    
    GRAY = "#D3D3D3"

    RED = "#FF0000"
    GREEN = "#008000"
    BLUE = "#0000FF"
    
    YELLOW = "#FFFF00"    
    PINK = "#FFC0CB"

    GRAY_OVERLAP = "#A9A9A9" #DarkGray

# Default factory functions    
def randomId():
    """Create a id, found something similar (nanoid) in the excalidraw code"""
    return ''.join(random.choice(string.ascii_letters+string.digits+"-_") for i in range(21)) #Nanoid 

def randomFileId():
    # Original Implementation does SHA1 by default and has a fallback to random range (Nanoid) of 40 chars.
    return ''.join(random.choice(string.ascii_letters+string.digits+"-_") for i in range(40)) #Nanoid 

def randomInt():
    """Create a random integer between 0, 1024, found it in the excalidraw code"""
    return random.randint(0, 1024)

def randomNonce():
    """Create a random integer, found it in the excalidraw code"""
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

@dataclasses.dataclass(kw_only=True)
class ExcalidrawImageElement(ExcalidrawElement):
      type: str = "image"

      scale: list[int] = dataclasses.field(default_factory=lambda: [1,1])
      fileId: str = ""
      status: str = "saved"

@dataclasses.dataclass()        
class ExcalidrawFile():
    id: str = dataclasses.field(default_factory=randomFileId) 
    mimeType: str =  "image/gif",
    dataURL: str = "data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==",
    created: int = dataclasses.field(default_factory=timestampInMiliseconds)
    lastRetrieved: int = dataclasses.field(default_factory=timestampInMiliseconds)
 
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

    def addFile(self, file: ExcalidrawFile):
        # the structure in the end needs to be <id>: { id: <id>, dateurl..} Not a list (mind blown)
        self.files[file.id] = dataclasses.asdict(file)

class DataclassJSONEncoder(json.JSONEncoder):
    """Encoder to convert a Dataclass to JSON"""
    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        return super().default(o)


# Conversion functions, this the control logic what to do
def blocks_to_excalidraw(blocks: Iterable[Block])-> ExcalidrawDocument:
    """Convert Blocks to Excalidraw.
    
    Currently supports:
      - SceneLineItemBlock
      - RootTextBlock
    """
    
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

# External functions called by CLI
def excalidrawDocument_to_str(document: ExcalidrawDocument) -> str:
    """Convert an ExcalidrawDocument to JSON string """
    return json.dumps(document, cls=DataclassJSONEncoder, indent=4)

def blocks_to_excalidraw_str(blocks: Iterable[Block]) -> str:
    "Convert blocks to excalidraw and return it as pretty JSON string"
    return excalidrawDocument_to_str(blocks_to_excalidraw(blocks))

# Conversion of a block to an specific element functions
def draw_stroke(block) -> ExcalidrawFreedrawElement:
    """Draw a pen stroke"""
    _logger.debug('Processing: SceneLineItemBlock')
    
    # Function always returns an ExcalidrawFreedrawElement
    excalidrawStroke = ExcalidrawFreedrawElement()
    if block.item.value is None:
        return excalidrawStroke
    
    # Eraser strokes are stored a penstrokes
    if block.item.value.tool == Pen.ERASER:
        excalidrawStroke.isDeleted = True
    
    # Set the color of the stroke
    excalidrawStroke.strokeColor = HexPenColors[block.item.value.color.name].value

    # Proces the points
    absolutePoints = []
    pressures = []
    for _ , point in enumerate(block.item.value.points):
        absolutePoints.append([point.x,point.y])
        pressures.append(point.pressure)
        #print(point.speed, point.direction, point.width, point.pressure)

    # Set the start the of the stroke
    excalidrawStroke.x = absolutePoints[0][0]
    excalidrawStroke.y = absolutePoints[0][1]
    
    # Create relative points based on the starting point
    relativePoints = []
    for ap in absolutePoints:
        x = ap[0] - excalidrawStroke.x
        y = ap[1] - excalidrawStroke.y
        relativePoints.append([x,y])

    excalidrawStroke.points = relativePoints

    # Take the pressure values as is, Excalidraw seems to use the same scale
    excalidrawStroke.pressures = pressures
    return excalidrawStroke


def draw_text(block) -> ExcalidrawTextElement:
    """Draw a textblock
    
    Note: Excalidraw doesnt support bold / italic, skipping the textformattig
    """
    _logger.debug('Processing: RootTextBlock')

    # Combine the separate text elements into one piece of text
    text = "".join([i[1] for i in block.value.items.items()])
    
    # Calculate the position
    x = block.value.pos_x + XPOS_SHIFT
    y = block.value.pos_y
    width = round(block.value.width) # We take this for granted, seems to be on the big side

    # To get line height in px, multiply with font size. Multiply by number of lines
    # https://github.com/excalidraw/excalidraw/blob/master/src/element/types.ts#L161
    height = ExcalidrawTextElement.fontSize * ExcalidrawTextElement.lineHeight * len(text.splitlines()) 
    
    return ExcalidrawTextElement(x=round(x), 
                                            y=round(y),
                                            width=round(width),
                                            height=round(height),
                                            text=text,
                                            originalText=text)
