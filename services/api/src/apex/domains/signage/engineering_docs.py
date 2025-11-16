"""
APEX Signage Engineering - Engineering Documentation Generation

Calculation sheets (LaTeX) and load diagrams (matplotlib/SVG).
"""

from __future__ import annotations

import base64
import io
from typing import Any, Dict, List, Optional

from jinja2 import Template
import numpy as np
from matplotlib import pyplot as plt

from .models import Cabinet, LoadDerivation, SiteLoads


# ========== Calculation Sheet Generation (LaTeX/PDF) ==========


CALC_SHEET_TEMPLATE = r"""
\documentclass[11pt]{article}
\usepackage{amsmath}
\usepackage{geometry}
\geometry{margin=1in}
\title{APEX Engineering Calculation Sheet}
\author{APEX Signage Engineering}
\date{\today}

\begin{document}
\maketitle

\section{Input Parameters}
\begin{itemize}
    \item Wind Speed: {{ wind_speed_mph }} mph
    \item Exposure Category: {{ exposure }}
    \item Sign Height: {{ height_ft }} ft
    \item Cabinet Area: {{ area_ft2 }} ft²
    \item Centroid Height: {{ z_cg_ft }} ft
\end{itemize}

\section{Load Derivation}
Per ASCE 7-22 Chapter 26, velocity pressure:
\begin{equation}
q_z = 0.00256 \times K_z \times K_{zt} \times K_d \times V^2 \times G
\end{equation}

Where:
\begin{itemize}
    \item $K_z = {{ kz }}$ (exposure factor)
    \item $K_{zt} = 1.0$ (topographic factor)
    \item $K_d = 0.85$ (directionality factor)
    \item $V = {{ wind_speed_mph }}$ mph
    \item $G = 0.85$ (gust effect factor)
\end{itemize}

Velocity pressure: $q_z = {{ q_psf }}$ psf

Service moment:
\begin{equation}
M_{service} = q_z \times A \times z_{cg} = {{ q_psf }} \times {{ area_ft2 }} \times {{ z_cg_ft }} = {{ m_svc_kipft }} \text{ kip-ft}
\end{equation}

Ultimate moment (LRFD load factor):
\begin{equation}
M_u = 1.6 \times M_{service} = {{ mu_kipft }} \text{ kip-ft}
\end{equation}

\section{References}
\begin{itemize}
    \item ASCE 7-22: Minimum Design Loads and Associated Criteria
    \item AISC 360-16: Specification for Structural Steel Buildings
    \item ACI 318: Building Code Requirements for Structural Concrete
\end{itemize}

\end{document}
"""


def generate_calc_sheet(
    site: SiteLoads,
    derived_loads: LoadDerivation,
    height_ft: float,
    cabinets: List[Cabinet],
    output_format: str = "latex",
) -> str:
    """
    Generate calculation sheet with equations and references.
    
    Args:
        site: Site loads
        derived_loads: Derived load calculations
        height_ft: Sign height
        cabinets: Cabinet list
        output_format: "latex" or "html"
    
    Returns:
        LaTeX or HTML string (can be compiled to PDF via pdflatex or weasyprint)
    """
    # Prepare template variables
    area_ft2 = sum(c.width_ft * c.height_ft for c in cabinets)
    
    # Recalculate for template (or use derived values)
    kz = 1.0  # Simplified
    q_psf = 0.00256 * kz * 1.0 * 0.85 * (site.wind_speed_mph**2) * 0.85
    m_svc_kipft = (q_psf * area_ft2 * derived_loads.z_cg_ft) / 1000.0
    
    template_vars = {
        "wind_speed_mph": site.wind_speed_mph,
        "exposure": site.exposure,
        "height_ft": height_ft,
        "area_ft2": round(area_ft2, 2),
        "z_cg_ft": round(derived_loads.z_cg_ft, 2),
        "kz": kz,
        "q_psf": round(q_psf, 2),
        "m_svc_kipft": round(m_svc_kipft, 2),
        "mu_kipft": round(derived_loads.mu_kipft, 2),
    }
    
    if output_format == "html":
        # HTML version for weasyprint
        html_template = Template("""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; margin: 1in; }
                h1 { color: #333; }
                .equation { margin: 20px 0; }
                .references { margin-top: 40px; }
            </style>
        </head>
        <body>
            <h1>APEX Engineering Calculation Sheet</h1>
            
            <h2>Input Parameters</h2>
            <ul>
                <li>Wind Speed: {{ wind_speed_mph }} mph</li>
                <li>Exposure: {{ exposure }}</li>
                <li>Sign Height: {{ height_ft }} ft</li>
                <li>Cabinet Area: {{ area_ft2 }} ft²</li>
            </ul>
            
            <h2>Load Derivation</h2>
            <p>Per ASCE 7-22 Chapter 26:</p>
            <div class="equation">
                q<sub>z</sub> = 0.00256 × K<sub>z</sub> × K<sub>zt</sub> × K<sub>d</sub> × V² × G
            </div>
            <p>Velocity pressure: q<sub>z</sub> = {{ q_psf }} psf</p>
            <p>Ultimate moment: M<sub>u</sub> = {{ mu_kipft }} kip-ft</p>
            
            <div class="references">
                <h2>References</h2>
                <ul>
                    <li>ASCE 7-22: Minimum Design Loads</li>
                    <li>AISC 360-16: Structural Steel Buildings</li>
                </ul>
            </div>
        </body>
        </html>
        """)
        return html_template.render(**template_vars)
    else:
        # LaTeX version
        template = Template(CALC_SHEET_TEMPLATE)
        return template.render(**template_vars)


def generate_calc_sheet_pdf(calc_sheet_content: str, output_path: Optional[str] = None) -> bytes:
    """
    Convert calculation sheet to PDF.
    
    Args:
        calc_sheet_content: LaTeX or HTML content
        output_path: Optional output file path
    
    Returns:
        PDF bytes
    """
    # For HTML, use weasyprint
    if calc_sheet_content.strip().startswith("<!DOCTYPE"):
        from weasyprint import HTML
        
        pdf_bytes = HTML(string=calc_sheet_content).write_pdf()
        return pdf_bytes
    
    # For LaTeX, would need pdflatex (external command)
    # Placeholder - would execute: pdflatex -output-directory /tmp file.tex
    raise NotImplementedError("LaTeX to PDF compilation requires pdflatex (not implemented)")


# ========== Load Diagram Generation (Matplotlib/SVG) ==========


def generate_load_diagram(
    derived_loads: LoadDerivation,
    height_ft: float,
    output_format: str = "svg",
) -> str:
    """
    Generate free-body diagram and moment diagram.
    
    Args:
        derived_loads: Derived load calculations
        height_ft: Sign height
        output_format: "svg" or "png"
    
    Returns:
        Base64-encoded SVG string or PNG bytes
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
    
    # Free-body diagram (left)
    ax1.set_aspect("equal")
    ax1.set_xlim(-2, 2)
    ax1.set_ylim(0, height_ft + 2)
    
    # Sign representation
    sign_width = 1.0
    sign_height = height_ft * 0.3
    sign_x = -sign_width / 2.0
    sign_y = height_ft - sign_height
    
    # Draw sign
    rect = plt.Rectangle((sign_x, sign_y), sign_width, sign_height, fill=True, color="lightblue", edgecolor="black")
    ax1.add_patch(rect)
    
    # Draw pole
    ax1.plot([0, 0], [0, height_ft], "k-", linewidth=3, label="Pole")
    
    # Draw loads
    wind_load_lbf = derived_loads.mu_kipft * 1000.0 / (derived_loads.z_cg_ft if derived_loads.z_cg_ft > 0 else height_ft)
    ax1.arrow(0.5, derived_loads.z_cg_ft, 0.5, 0, head_width=0.2, head_length=0.1, fc="red", ec="red")
    ax1.text(1.2, derived_loads.z_cg_ft, f"F={wind_load_lbf:.0f} lbf", fontsize=10)
    
    # Ground reaction
    ax1.arrow(0, 0, 0, -0.5, head_width=0.2, head_length=0.1, fc="green", ec="green")
    ax1.text(-0.5, -0.5, "R", fontsize=10)
    
    ax1.set_xlabel("Distance (ft)")
    ax1.set_ylabel("Height (ft)")
    ax1.set_title("Free-Body Diagram")
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # Moment diagram (right)
    z_points = np.linspace(0, height_ft, 100)
    moment_points = derived_loads.mu_kipft * (z_points / height_ft)
    
    ax2.plot(moment_points, z_points, "b-", linewidth=2, label="Moment")
    ax2.fill_betweenx(z_points, 0, moment_points, alpha=0.3, color="blue")
    ax2.set_xlabel("Moment (kip-ft)")
    ax2.set_ylabel("Height (ft)")
    ax2.set_title("Moment Diagram")
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    # Save to buffer
    buf = io.BytesIO()
    
    if output_format == "svg":
        fig.savefig(buf, format="svg", bbox_inches="tight")
        buf.seek(0)
        svg_content = buf.read().decode("utf-8")
        plt.close(fig)
        return base64.b64encode(svg_content.encode("utf-8")).decode("utf-8")
    else:
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        buf.seek(0)
        png_bytes = buf.read()
        plt.close(fig)
        return base64.b64encode(png_bytes).decode("utf-8")

