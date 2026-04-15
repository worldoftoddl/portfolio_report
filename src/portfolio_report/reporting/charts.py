"""Plotly 차트 조립 모듈.

설계 원칙:
- 각 함수는 go.Figure를 반환하거나, 기존 Figure 위에 trace를 추가.
- overlay (가격 차트와 같은 y축): 이동평균, 일목균형표, 볼린저밴드
- subplot (별도 y축 패널): RSI, MACD
- compose_chart: 여러 지표를 하나의 Figure로 조립

나중에 FastAPI/Streamlit으로 전환 시 재사용 가능.
"""

from __future__ import annotations

from typing import Literal

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

Overlay = Literal["ichimoku", "bb"]
Subplot = Literal["rsi", "macd"]


# --- 기본 캔들스틱 ---

def base_candle(df: pd.DataFrame, name: str = "") -> go.Figure:
    """OHLC 캔들스틱만 포함한 Figure."""
    fig = go.Figure()
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name=name or "가격",
            increasing_line_color="#e74c3c",
            decreasing_line_color="#3498db",
        )
    )
    fig.update_layout(
        xaxis_rangeslider_visible=False,
        template="plotly_white",
        height=600,
        title=name,
        hovermode="x unified",
    )
    return fig


# --- 오버레이 ---

def add_ichimoku(fig: go.Figure, df: pd.DataFrame, row: int = 1, col: int = 1) -> go.Figure:
    """일목균형표 (전환선/기준선/선행스팬/후행스팬 + 구름대 음영)."""
    kwargs_rc = {"row": row, "col": col}
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df["ITS_9"], name="전환선(9)",
            line={"color": "#e74c3c", "width": 1},
        ),
        **kwargs_rc,
    )
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df["IKS_26"], name="기준선(26)",
            line={"color": "#3498db", "width": 1},
        ),
        **kwargs_rc,
    )
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df["ISA_9"], name="선행스팬A",
            line={"color": "rgba(46,204,113,0.5)", "width": 1},
        ),
        **kwargs_rc,
    )
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df["ISB_26"], name="선행스팬B",
            line={"color": "rgba(231,76,60,0.5)", "width": 1},
            fill="tonexty", fillcolor="rgba(150,150,150,0.15)",
        ),
        **kwargs_rc,
    )
    return fig


def add_bollinger(fig: go.Figure, df: pd.DataFrame, row: int = 1, col: int = 1) -> go.Figure:
    """볼린저밴드 (상/중/하)."""
    kwargs_rc = {"row": row, "col": col}
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df["BBU_20_2.0_2.0"], name="BB 상단",
            line={"color": "rgba(155,89,182,0.6)", "width": 1, "dash": "dash"},
        ),
        **kwargs_rc,
    )
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df["BBM_20_2.0_2.0"], name="BB 중앙",
            line={"color": "rgba(155,89,182,0.8)", "width": 1},
        ),
        **kwargs_rc,
    )
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df["BBL_20_2.0_2.0"], name="BB 하단",
            line={"color": "rgba(155,89,182,0.6)", "width": 1, "dash": "dash"},
            fill="tonexty", fillcolor="rgba(155,89,182,0.08)",
        ),
        **kwargs_rc,
    )
    return fig


# --- 서브플롯 ---

def rsi_subplot(fig: go.Figure, df: pd.DataFrame, row: int, col: int = 1) -> go.Figure:
    """RSI 패널: 70 과매수 / 30 과매도 기준선 포함."""
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df["RSI_14"], name="RSI(14)",
            line={"color": "#9b59b6", "width": 1.5},
        ),
        row=row, col=col,
    )
    fig.add_hline(y=70, line_dash="dot", line_color="red", row=row, col=col)
    fig.add_hline(y=30, line_dash="dot", line_color="green", row=row, col=col)
    fig.update_yaxes(range=[0, 100], row=row, col=col, title_text="RSI")
    return fig


def macd_subplot(fig: go.Figure, df: pd.DataFrame, row: int, col: int = 1) -> go.Figure:
    """MACD 패널: MACD 라인 + 시그널 + 히스토그램."""
    fig.add_trace(
        go.Bar(
            x=df.index, y=df["MACDh_12_26_9"], name="MACD 히스토그램",
            marker_color=[
                "#e74c3c" if v >= 0 else "#3498db" for v in df["MACDh_12_26_9"].fillna(0)
            ],
        ),
        row=row, col=col,
    )
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df["MACD_12_26_9"], name="MACD",
            line={"color": "#2c3e50", "width": 1.5},
        ),
        row=row, col=col,
    )
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df["MACDs_12_26_9"], name="Signal",
            line={"color": "#e67e22", "width": 1.5, "dash": "dash"},
        ),
        row=row, col=col,
    )
    fig.update_yaxes(title_text="MACD", row=row, col=col)
    return fig


# --- 조립 ---

def compose_chart(
    df: pd.DataFrame,
    overlays: list[Overlay],
    subplots: list[Subplot],
    title: str = "",
) -> go.Figure:
    """가격 + 오버레이 + 서브플롯을 하나의 Figure로 조립.

    레이아웃: 가격 차트(상단, 60%) + 각 subplot(20% 씩)
    """
    total_rows = 1 + len(subplots)
    row_heights = [0.6] + [0.4 / len(subplots)] * len(subplots) if subplots else [1.0]

    fig = make_subplots(
        rows=total_rows,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=row_heights,
        subplot_titles=[title] + [s.upper() for s in subplots] if subplots else [title],
    )

    # 가격 차트
    fig.add_trace(
        go.Candlestick(
            x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
            name="가격",
            increasing_line_color="#e74c3c",
            decreasing_line_color="#3498db",
        ),
        row=1, col=1,
    )

    # 오버레이
    if "bb" in overlays:
        add_bollinger(fig, df, row=1, col=1)
    if "ichimoku" in overlays:
        add_ichimoku(fig, df, row=1, col=1)

    # 서브플롯
    for i, sp in enumerate(subplots, start=2):
        if sp == "rsi":
            rsi_subplot(fig, df, row=i)
        elif sp == "macd":
            macd_subplot(fig, df, row=i)

    fig.update_layout(
        xaxis_rangeslider_visible=False,
        template="plotly_white",
        height=400 + 200 * len(subplots),
        hovermode="x unified",
        showlegend=True,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
    )
    return fig
