Attribute VB_Name = "MarketPrice"
Option Explicit

Public Sub AnalyzeWithMarketPrice()
    RunPython "from marketprice.excel_bridge import main; main()"
End Sub
