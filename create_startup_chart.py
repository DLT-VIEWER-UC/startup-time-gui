import openpyxl
from openpyxl.chart import BarChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.drawing.line import LineProperties
from openpyxl.drawing.colors import ColorChoice
from openpyxl.chart.layout import Layout, ManualLayout
import math

# -------------------------
# Fixed chart box size (user-provided)
# -------------------------
FIXED_CHART_WIDTH = 18   # openpyxl chart width units
FIXED_CHART_HEIGHT = 5  # openpyxl chart height units
# -------------------------

# Sample data (replace/extend as needed)
data = [
    ["Application", "QNX Startup", "App Startup", "Total"],
    ["Navigation", 1.5, 1.7, 3.2],
    ["Media Player", 1.5, 1.3, 2.8],
    ["Climate Control", 1.5, 0.6, 2.1],
    ["Phone", 1.5, 0.4, 1.9],
    ["Settings", 1.5, 1.0, 2.5],
    ["Voice Assistant", 1.5, 1.5, 3.0],
    ["Camera1", 1.5, 0.8, 2.3],
    ["Camera2", 1.5, 0.8, 2.3],
    # add rows to test many bars...
]

# create workbook & sheet
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Startup Time Data"

for row in data:
    ws.append(row)

num_bars = max(0, len(data) - 1)
max_value = max([r[3] for r in data[1:]]) if num_bars else 0  # Use Total column for max
x_axis_max = math.ceil(max_value) + 1

# create and configure chart as combo
chart = BarChart()
chart.type = "col"  # Change to combo chart type
chart.grouping = "stacked"  # Enable stacked bars for first two series
chart.style = None  # Remove style to prevent default shadows
chart.title = "Applications Startup Time from IG-ON on ELITE SoC1"
chart.y_axis.title = "Startup Time (s)  *The first 1.5 seconds is the QNX startup time"
chart.x_axis.title = "Applications"
chart.legend = None

# try to overlay the title so it does not use plot area vertical space
try:
    chart.title.overlay = True
except Exception:
    # older openpyxl versions may not support overlay; ignore if unavailable
    pass

# gridlines
grey_line = LineProperties(solidFill=ColorChoice(srgbClr="D3D3D3"))
grey_props = GraphicalProperties(ln=grey_line)
chart.y_axis.majorGridlines = openpyxl.chart.axis.ChartLines()
chart.y_axis.majorGridlines.spPr = grey_props
chart.x_axis.majorGridlines = openpyxl.chart.axis.ChartLines()
chart.x_axis.majorGridlines.spPr = grey_props

# axis scaling with small buffer on right
chart.x_axis.scaling.min = 0
chart.x_axis.scaling.max = x_axis_max + max(0.5, 0.12 * x_axis_max)
chart.x_axis.scaling.orientation = "minMax"
chart.x_axis.delete = False
chart.y_axis.delete = False

# data refs
# First chart gets only the first two series (QNX Startup and App Startup)
data_ref = Reference(ws, min_col=2, min_row=1, max_row=len(data), max_col=3)
cats_ref = Reference(ws, min_col=1, min_row=2, max_row=len(data))
chart.add_data(data_ref, titles_from_data=True)
chart.set_categories(cats_ref)

# color bars - three series
# Series 1: QNX Startup (constant 1.5) - Red with no border/shadow
from openpyxl.drawing.effect import EffectList

series1 = chart.series[0]
gp1 = GraphicalProperties(solidFill=ColorChoice(srgbClr="FF6B6B"))  # Red color
# Remove border by setting line to no fill
no_line = LineProperties()
no_line.noFill = True
gp1.ln = no_line
# Remove shadow completely - set both shadow and effectLst to empty/None
gp1.shadow = None
gp1.effectLst = EffectList()  # Empty effect list instead of None
series1.graphicalProperties = gp1

# Series 2: App Startup (variable) - Blue with no border/shadow
series2 = chart.series[1]
gp2 = GraphicalProperties(solidFill=ColorChoice(srgbClr="4472C4"))  # Blue color
# Remove border by setting line to no fill
no_line2 = LineProperties()
no_line2.noFill = True
gp2.ln = no_line2
# Remove shadow completely - set both shadow and effectLst to empty/None
gp2.shadow = None
gp2.effectLst = EffectList()  # Empty effect list instead of None
series2.graphicalProperties = gp2

# Series 3: Total - Add as clustered bar to the same chart
# Add the Total column data (column 4) separately
data_ref_total = Reference(ws, min_col=4, min_row=1, max_row=len(data))
chart.add_data(data_ref_total, titles_from_data=True)

# Style the third series with transparency
series3 = chart.series[2]
gp3 = GraphicalProperties()
gp3.noFill = True  # No fill
# Remove border by setting line to no fill
no_line3 = LineProperties()
no_line3.noFill = True
gp3.ln = no_line3
# Remove shadow completely - set both shadow and effectLst to empty/None
gp3.shadow = None
gp3.effectLst = EffectList()  # Empty effect list instead of None
series3.graphicalProperties = gp3

# Make the third series clustered (not stacked)
series3.overlap = 0  # No overlap for clustered effect

# set fixed size
chart.width = FIXED_CHART_WIDTH
chart.height = FIXED_CHART_HEIGHT

# gapWidth heuristic: increase gap (thinner bars) when many bars exist
BASE_GAP = 220
BASE_BARS = 10
min_gap = 10
max_gap = 2000
if num_bars <= 0:
    gap = BASE_GAP
else:
    # more aggressive thinning: use sqrt scaling to avoid extreme thinness too quickly
    scale = math.sqrt(max(1, num_bars / BASE_BARS))
    gap = int(BASE_GAP * scale)
    gap = max(min_gap, min(max_gap, gap))
chart.gapWidth = gap
chart.overlap = 100  # Set series overlap to 100% (fully overlapped)

# try to reduce label density if too many bars for chart height
LABELS_PER_UNIT = 3.5
max_visible_labels = max(2, int(FIXED_CHART_HEIGHT * LABELS_PER_UNIT))
if num_bars > max_visible_labels:
    skip = math.ceil(num_bars / max_visible_labels)
    try:
        chart.y_axis.tickLblSkip = skip
    except Exception:
        pass
else:
    try:
        chart.y_axis.tickLblSkip = 1
    except Exception:
        pass
    
    openpyxl.chart.label.DataLabelList

# data labels: place inside base (left) to avoid needing right-side space
chart.dataLabels = DataLabelList()
chart.dataLabels.showVal = True
chart.dataLabels.showCatName = False
chart.dataLabels.showSerName = False
chart.dataLabels.showLegendKey = False
for pos in ("inBase", "insideBase", "inEnd", "insideEnd"):
    try:
        chart.dataLabels.dLblPos = pos
        break
    except Exception:
        try:
            setattr(chart.dataLabels, "dLblPos", pos)
            break
        except Exception:
            continue

# MANUAL LAYOUT with padding — define the plot area boundaries
# Add padding on all sides to prevent clipping
left_padding = 0.15    # 15% left margin for y-axis labels
top_padding = 0.12     # 12% top margin for title
right_padding = 0.05   # 5% right margin
bottom_padding = 0.10  # 10% bottom margin for x-axis labels

plot_width = 1.0 - left_padding - right_padding
plot_height = 1.0 - top_padding - bottom_padding

ml = ManualLayout()
ml.x = left_padding
ml.y = top_padding
ml.w = plot_width
ml.h = plot_height
ml.xMode = "edge"  # Position from edge
ml.yMode = "edge"  # Position from edge
ml.wMode = "edge"  # Width relative to chart
ml.hMode = "edge"  # Height relative to chart

chart.layout = Layout(manualLayout=ml)

# final safe guard: if there are extremely many bars (hundreds),
# further increase gapWidth so bars are not overlapping visually
if num_bars > 100:
    chart.gapWidth = min(chart.gapWidth * 2, max_gap)

# place chart and save
ws.column_dimensions['A'].width = 28
ws.column_dimensions['B'].width = 15

# anchor chart where there is more sheet space (B2 typically)
ws.add_chart(chart, "B2")

output_file = "Startup_Time_Chart_AutoFit_FixedSize_v3.xlsx"
wb.save(output_file)
print(f"Saved '{output_file}' with {num_bars} bars, chart.width={chart.width}, chart.height={chart.height}, gapWidth={chart.gapWidth}")