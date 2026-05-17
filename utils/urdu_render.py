import arabic_reshaper
from bidi.algorithm import get_display

# Standard Urdu Reshaper configuration
# Preserves ligatures and handles Nastaliq specifics
URDU_RESHAPER_CONFIG = {
    'language': 'Urdu',
    'delete_harakat': False,
    'shift_harakat_position': False,
    'support_ligatures': True,
    'use_unshaped_instead_of_isolated': False
}

urdu_reshaper = arabic_reshaper.ArabicReshaper(configuration=URDU_RESHAPER_CONFIG)

def format_for_console(text: str) -> str:
    """
    Renders Urdu correctly for the terminal ONLY.
    Processes line-by-line to prevent multi-line reversal bugs and
    preserves correct LTR/RTL flow for mixed text.
    """
    if not isinstance(text, str):
        return str(text)
    
    rendered_lines = []
    for line in text.split('\n'):
        if not line.strip():
            rendered_lines.append(line)
        else:
            reshaped = urdu_reshaper.reshape(line)
            # base_dir='R' forces RTL context for mixed strings, making sure
            # English numbers or letters inside Urdu sentences don't mess up the overall direction.
            bidi_text = get_display(reshaped, base_dir='R')
            rendered_lines.append(bidi_text)
            
    return '\n'.join(rendered_lines)



def format_for_export(text: str) -> str:
    """
    Exporting to PDF/HTML should NOT use python-bidi or reshaping explicitly.
    Modern engines (Weasyprint, HTML browsers, React Native, etc.) handle RTL natively.
    We just ensure proper UTF-8 decoding/encoding and string sanitation.
    """
    if not isinstance(text, str):
        return str(text)
    
    # Return raw text safely decoded, leaving bidi control to the renderer engine
    return text.encode('utf-8', 'ignore').decode('utf-8')
