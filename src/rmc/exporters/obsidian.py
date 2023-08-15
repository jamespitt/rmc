from .excalidraw import ExcalidrawDocument, ExcalidrawTextElement, excalidrawDocument_to_str

template = """---

excalidraw-plugin: parsed
tags: [excalidraw]

---
==⚠  Switch to EXCALIDRAW VIEW in the MORE OPTIONS menu of this document. ⚠==


# Text Elements
{text_elements}
%%
# Drawing
```json
{excalidraw_json}
```
%%"""


def excalidraw_to_obsidian(document: ExcalidrawDocument):
    excalidraw_str = excalidrawDocument_to_str(document)
    text_elements = [] 
    
    for element in document.elements:
        if isinstance(element, ExcalidrawTextElement):
            text_elements.append(element.text)
    
    print(template.format(text_elements="\n\n".join(text_elements),
                          excalidraw_json=excalidraw_str))

