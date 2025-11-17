from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.drawing.colors import ColorChoice
from openpyxl.chart.axis import ChartLines
from openpyxl.drawing.line import LineProperties
from openpyxl.chart.layout import Layout, ManualLayout


def create_workbook_with_data(data, sheet_title="Startup Time Data"):
    """Create a workbook and populate it with data."""
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_title
    
    for row in data:
        ws.append(row)
    
    return wb, ws


def create_data_references(ws, data):
    """Create references for chart data."""
    cats = Reference(ws, min_col=1, min_row=2, max_row=len(data))
    stacked_data = Reference(ws, min_col=2, max_col=3, min_row=1, max_row=len(data))
    clustered_data = Reference(ws, min_col=4, max_col=4, min_row=1, max_row=len(data))
    
    return cats, stacked_data, clustered_data

def create_stacked_chart(stacked_data, cats, title, y_title, x_title):
    """Create and configure the stacked bar chart."""
    stacked = BarChart()
    stacked.type = "bar"
    stacked.grouping = "stacked"
    stacked.overlap = 100
    stacked.add_data(stacked_data, titles_from_data=True)
    stacked.set_categories(cats)
    stacked.title = title
    stacked.y_axis.title = y_title
    stacked.x_axis.title = x_title
    stacked.legend = None
    
    # Ensure axes are visible
    stacked.y_axis.delete = False
    stacked.x_axis.delete = False
    
    # Position category axis at the bottom
    stacked.y_axis.tickLblPos = "low"
    stacked.x_axis.crosses = "min"
    
    return stacked


def create_clustered_chart(clustered_data, cats, gap_width=100):
    """Create and configure the clustered bar chart for secondary axis."""
    clustered = BarChart()
    clustered.type = "bar"
    clustered.grouping = "clustered"
    clustered.overlap = 0
    clustered.add_data(clustered_data, titles_from_data=True)
    clustered.set_categories(cats)
    
    # Configure secondary axis
    clustered.y_axis.axId = 200
    clustered.y_axis.tickLblPos = "low"
    clustered.x_axis.crosses = "min"
    clustered.gapWidth = gap_width
    
    # Disable major gridlines for secondary axis
    clustered.y_axis.majorGridlines = None
    
    return clustered

def add_gridlines(chart, color="D3D3D3"):
    """Add gridlines to the chart."""
    grey_line = LineProperties(solidFill=ColorChoice(srgbClr=color))
    grey_props = GraphicalProperties(ln=grey_line)
    chart.y_axis.majorGridlines = ChartLines()
    chart.y_axis.majorGridlines.spPr = grey_props
    chart.x_axis.majorGridlines = ChartLines()
    chart.x_axis.majorGridlines.spPr = grey_props


def configure_chart_layout(chart, width=18, height=10, gap_width=100, major_unit=1):
    """Configure chart size, layout, and axis settings."""
    # Set axis major unit
    chart.y_axis.majorUnit = major_unit
    
    # Set chart sizing
    chart.gapWidth = gap_width
    chart.width = width
    chart.height = height
    
    # Set manual layout with padding
    ml = ManualLayout()
    ml.x = 0.10
    ml.y = 0.08
    ml.w = 0.87
    ml.h = 0.87
    ml.xMode = "edge"
    ml.yMode = "edge"
    ml.wMode = "edge"
    ml.hMode = "edge"
    chart.layout = Layout(manualLayout=ml)

def customize_stacked_series(chart, colors=["deebf7", "ffbf00"]):
    """Customize appearance and data labels for stacked series."""
    for i, ser in enumerate(chart.series):
        # Data labels - show only values
        ser.dLbls = DataLabelList()
        ser.dLbls.showVal = True
        ser.dLbls.showCatName = False
        ser.dLbls.showSerName = False
        ser.dLbls.showLegendKey = False

        if i < len(colors):
            # Apply colors to series
            gp = GraphicalProperties()
            gp.solidFill = ColorChoice(srgbClr=colors[i])
            ser.graphicalProperties = gp


def customize_clustered_series(chart, transparent=True, label_position="outEnd"):
    """Customize appearance and data labels for clustered series."""
    for i, ser in enumerate(chart.series):
        # Data labels - show only values
        ser.dLbls = DataLabelList()
        ser.dLbls.showVal = True
        ser.dLbls.showCatName = False
        ser.dLbls.showSerName = False
        ser.dLbls.showLegendKey = False
        ser.dLbls.dLblPos = label_position
        
        if transparent:
            # Make series completely transparent
            gp = GraphicalProperties()
            gp.noFill = True
            
            # Remove border
            no_line = LineProperties()
            no_line.noFill = True
            gp.ln = no_line
            
            ser.graphicalProperties = gp


def create_combo_chart(ws, data, output_file="Ramesh_combo_chart_secondary_axis.xlsx"):
    """Main function to create the combo chart with all configurations."""
    # Create data references
    cats, stacked_data, clustered_data = create_data_references(ws, data)
    
    # Create charts
    stacked = create_stacked_chart(
        stacked_data, cats,
        title="Applications Startup Time from IG-ON",
        y_title="Startup Time (s)  *The first 1.5 seconds is the QNX startup time",
        x_title="Applications"
    )
    
    clustered = create_clustered_chart(clustered_data, cats, gap_width=100)
    
    # Combine charts
    stacked += clustered
    
    # Add gridlines and configure layout
    add_gridlines(stacked)
    configure_chart_layout(stacked, width=18, height=10, gap_width=100, major_unit=1)
    
    # Customize series
    customize_stacked_series(stacked, colors=["deebf7", "ffbf00"])
    customize_clustered_series(clustered, transparent=True, label_position="outEnd")
    
    # Place chart on worksheet
    ws.add_chart(stacked, "E5")
    
    return stacked


def main():
    """Main execution function."""
    # Sample data
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
        ["Camera3", 1.5, 0.8, 2.3],
        ["Camera4", 1.5, 0.8, 2.3]
    ]
    
    # Create workbook with data
    wb, ws = create_workbook_with_data(data, "Startup Time Data")
    
    # Create combo chart
    create_combo_chart(ws, data)
    
    # Save workbook
    output_file = "Ramesh_combo_chart_secondary_axis.xlsx"
    wb.save(output_file)
    print(f"{output_file} created successfully.")


if __name__ == "__main__":
    main()
