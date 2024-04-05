import plotly.express as px

from dataclasses import dataclass

@dataclass
class CyclingPlotStyles:
    c_rate_colormap = px.colors.qualitative.Plotly
    marker_size: float = 12
    font_size: float = 14