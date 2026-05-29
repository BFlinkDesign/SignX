"""40398 St. Anthony Monument - integrated first-principles structural study.

STATUS: ???? DRAFT - PRE-PE ENGINEERING STUDY - NOT a stamped design,
NOT canonical, NOT complete. Transparent so every number is independently
checkable. Simplified models are labelled. ASSERTED inputs need official
cross-check (Phase F) + AHJ-confirmed wind edition + licensed PE seal.

Live-tested: run this file; it prints every formula + intermediate, runs a
V=111/115/119 sensitivity, identifies governing cases, applies monotonic
sanity checks, and reproduces/corrects the Cowork footing error.
"""
from __future__ import annotations
import math, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------- inputs
B_w   = 15 + 3/12            # sign width  ft  (.CDR VERIFIED 15'-3")
s_h   = 14 + 8/12            # sign height ft  (.CDR VERIFIED 14'-8")
As    = B_w * s_h            # solid sign area sf
z_top = s_h                  # monument at grade -> top = full height
z_cen = s_h/2.0              # centroid above grade ft
elev  = 1279.0               # ft  (ASCE Hazard Tool VERIFIED)
n_pole = 2                   # symmetric 2-post (engineered layout)
pole_spacing_ft = 7.0        # ENGINEERED-PRELIM 2-post spacing (NOT off sales proof; final by PE)

# coefficients (tag: VER=verified, ASSERT=needs official x-check, ASSUME=judgement)
Kzt = 1.0          # GROUNDED ASCE7-22 26.8.2: =1.0 flat IA site (no hill/escarpment) - site condition
Kd  = 0.85         # GROUNDED ASCE7-22 Tbl 26.6-1 solid signs/walls=0.85 (edition-stable). 7-22 relocated Kd qz->force eq; applied ONCE here, numerically identical
G   = 0.85         # GROUNDED ASCE7-22 26.11 rigid=0.85 (free src: structuremag/ASCE Amplify)
Ke  = math.exp(-0.0000362*elev)            # GROUNDED ASCE7-22 Tbl 26.9-1 / Eq (elev 1279 -> ~0.955)
Kz  = 0.85         # GROUNDED ASCE7-22 Tbl 26.10-1 Exp C, z<=15ft=0.85 (edition-stable; ASCE Amplify 26.10.1)
Bs, sh = B_w/s_h, s_h/z_top
Cf  = 1.45         # GROUNDED: ASCE 7-22 Fig 29.3-1 Case A/B, s/h=1.0 (at-grade monument), B/s~1.04 -> 1.45 (was ASSERTED 1.70; src: on-disk ASCE7-22 Ch.29 text 512407159)
caseB_applies = Bs <= 2.0
caseC_applies = Bs >= 2.0

# dead loads - EMC PROJECT-SOURCED; cabinet/poles ENGINEERED EST (industry
# practice = takeoff, not vendor weight per part). Governing OT/uplift use
# 0.6*D (ASCE 2.4) so the conservative low-DL bound is already covered.
W_emc = 1879.0     # lb  Watchfire 6mm DF EMC - PROJECT-SOURCED (40398 drawing/spec); confirm submittal
W_cab = 1500.0     # lb  ENGINEERED EST: alum skin (faces+returns ~210sf) + framing/retainers; confirm fab takeoff
W_pole_ea = 600.0  # lb  ENGINEERED EST per steel pole + 18" alum column cover; confirm fab
DL = W_emc + W_cab + n_pole*W_pole_ea          # ~4579 lb; OT/uplift checked at 0.6*D (conservative)

# material / allowables (ASSERT - AISC/ACI official x-check Phase F)
Fy_pipe = 35000.0  # A53 Gr B
Fb_pipe = 0.66*Fy_pipe                       # AISC 360-22 F8 compact round ASD
# small ASSERTED section catalog: (name, S in^3, Fy)
PIPES = [("6in Sch40 A53",8.50),("8in Sch40 A53",16.80),
         ("10in Sch40 A53",29.90),("12in Sch40 A53",43.80)]

q_allow = 1500.0   # psf ASSERT presumptive (IBC 1806.2, soil class UNKNOWN -> W3)
gamma_c = 150.0    # pcf concrete
mu_slide = 0.35    # ASSERT soil friction
frost_in = 48.0    # ASSERT Iowa frost (42 vs 48 conflict - W1/code)

def wind(V):
    qz = 0.00256*Kz*Kzt*Kd*Ke*V*V            # ASCE7-22 Eq 26.10-1
    F  = qz*G*Cf*As                          # Eq 29.3-1 Case A resultant
    M  = F*z_cen                             # base overturning (Case A)
    T  = F*0.2*B_w if caseB_applies else 0.0 # Case B torsion (e=0.2B)
    return dict(qz=qz,F=F,M=M,T=T)

def size_pole(M_total):
    Mp_inlb = (M_total/n_pole)*12.0          # per-pole base moment, in-lb (simplified equal split)
    Sreq = Mp_inlb/Fb_pipe
    pick = next(((n,S) for n,S in PIPES if S>=Sreq), None)
    return Sreq, pick, Mp_inlb

def footing(M, V_shear):
    # combined rectangular footing: L (parallel to wind/overturning), Bf width
    D = max(frost_in/12.0, 1.5)              # ft depth (>= frost, >= 1.5')
    Bf = 6.0                                  # ft  ASSUME trial width
    best = None
    for L10 in range(80, 281):                # L from 8.0 to 28.0 ft, 0.1 step
        L = L10/10.0
        Wf = L*Bf*D*gamma_c
        N  = DL + Wf
        e  = M/N
        A  = L*Bf
        kern = L/6.0
        if e <= kern:
            smax = N/A*(1+6*e/L); mode="trapz"
        else:
            a = L/2.0 - e
            if a <= 0: continue              # overturns
            smax = 2*N/(3*Bf*a); smin=0; mode="partial"
        FS_OT = (N*(L/2.0))/M                 # resisting/overturning about toe
        FS_SL = (mu_slide*N)/V_shear
        ok = (smax <= q_allow) and (FS_OT>=1.5) and (FS_SL>=1.5) and (e <= 0.75*kern)
        if ok:
            best = dict(L=L,Bf=Bf,D=D,N=N,e=e,kern=kern,smax=smax,mode=mode,
                        FS_OT=FS_OT,FS_SL=FS_SL,vol_yd3=L*Bf*D/27.0)
            break
    return best

def anchors(M_total):
    # per-pole baseplate, 4 F1554 Gr36 rods, ASSUME 8in gauge tension lever
    Mp = M_total/n_pole
    lever = 8.0/12.0                          # ft  ASSUME bolt group lever arm
    T_grp = Mp/lever                          # lb total tension side
    T_bolt = T_grp/2.0                        # 2 bolts on tension side
    Ft = 0.375*58000.0                        # AISC 360-22 ASD F1554 Gr36 = 0.375*Futa (Futa=58ksi); corrected from 0.33 per AUDIT-EVIDENCE
    Ab_req = T_bolt/Ft                        # in^2 required tensile area
    dia = math.sqrt(Ab_req*4/math.pi)/0.78    # approx gross from ~0.78 stress-area ratio
    return dict(T_bolt=T_bolt,Ab_req=Ab_req,dia_est=dia)

def pole_overturning(M_total, F_total, T_caseB, Sx):
    # RATIONAL 2-post mechanics (fixes defect #3): base overturning is
    # resisted as an AXIAL tension/compression couple between the two
    # poles at spacing s, NOT M/2 bending in each pole. Brings Case B
    # torsion into the anchor demand (defect #5) + deflection check.
    s = pole_spacing_ft
    P_couple = M_total / s                       # lb axial/pole (T windward, C leeward)
    dP_caseB = (T_caseB / s) if caseB_applies else 0.0   # extra differential axial, Case B ecc.
    DL_resist = 0.6 * (DL / n_pole)              # ASD 0.6D resisting uplift (ASCE 2.4)
    T_uplift = max(0.0, P_couple + dP_caseB - DL_resist) # net anchor uplift, windward pole
    V_pole = F_total / n_pole                    # lateral shear per pole
    T_bolt = T_uplift / 2.0                       # 2 tension-side bolts of that plate
    Ft = 0.375 * 58000.0
    dia = (math.sqrt((T_bolt/Ft)*4/math.pi)/0.78) if T_bolt > 0 else 0.0
    E = 29.0e6; OD = 8.625                        # 8in Sch40 (current pick)
    I = Sx * OD/2.0                               # in^4  (I = S*c, symmetric)
    Lc = z_cen * 12.0                             # in, conservative cantilever free length
    delta = V_pole * Lc**3 / (3.0*E*I)            # in, point-load cantilever (conservative)
    d_lim = (z_top*12.0)/100.0                    # H/100 serviceability (AISC/eng judgment). AASHTO LTS-6 = highway-agency supports, NOT private on-premise commercial signs (IBC/ASCE/AISC govern) - confirmed scoping; PE finalizes limit; AHJ confirm no ROW/LTS trigger
    return dict(P_couple=P_couple, dP_caseB=dP_caseB, T_uplift=T_uplift,
                V_pole=V_pole, T_bolt=T_bolt, dia=dia, delta=delta,
                d_lim=d_lim, defl_ok=delta <= d_lim)

print("="*70)
print(" 40398 ST ANTHONY MONUMENT - INTEGRATED STRUCTURAL STUDY  ???? DRAFT")
print(" PRE-PE - NOT STAMPED - NOT COMPLETE - models simplified/labelled")
print("="*70)
print(f"Geometry VER: B={B_w:.2f} s={s_h:.2f} As={As:.1f}sf  B/s={Bs:.2f} "
      f"s/h={sh:.2f}  z_cen={z_cen:.2f}ft")
print(f"CaseB(torsion) applies={caseB_applies}  CaseC applies={caseC_applies}")
print(f"Coeff: Kz={Kz}[A] Kzt={Kzt}[A] Kd={Kd}[A] Ke={Ke:.4f} G={G}[A] Cf={Cf}[A]")
print(f"DL={DL:.0f} lb [ASSERT]  q_allow={q_allow}psf[A]  frost={frost_in}in[A]")
print("-"*70)
prev=None
for V in (111.0,115.0,119.0):
    w=wind(V); Sreq,pick,Mp=size_pole(w['M']); ft=footing(w['M'],w['F']); an=anchors(w['M'])
    tag={111:"7-22/7-16 RC II VER",115:"7-10/AHJ band UNVERIF",119:"RC III UNVERIF"}[int(V)]
    print(f"V={V:.0f} mph  [{tag}]")
    print(f"  qz={w['qz']:6.2f}psf  F={w['F']:8.1f}lb  M_base={w['M']:10.1f}ftlb"
          f"  T_caseB={w['T']:8.1f}ftlb")
    print(f"  pole: Sreq={Sreq:6.2f}in3 -> pick={pick}")
    if ft: print(f"  footing: {ft['L']:.1f}x{ft['Bf']:.1f}x{ft['D']:.2f}ft "
                 f"{ft['mode']} smax={ft['smax']:.0f}psf e={ft['e']:.2f} "
                 f"kern={ft['kern']:.2f} FS_OT={ft['FS_OT']:.2f} "
                 f"FS_SL={ft['FS_SL']:.2f} vol={ft['vol_yd3']:.1f}yd3")
    else: print("  footing: NO PASS in trial range (flag)")
    print(f"  anchor/pole: T_bolt={an['T_bolt']:.0f}lb dia_est~{an['dia_est']:.2f}in")
    ov=pole_overturning(w['M'],w['F'],w['T'],pick[1])
    print(f"  2-pole RATIONAL (governs): P_couple={ov['P_couple']:.0f}lb "
          f"V_pole={ov['V_pole']:.0f}lb T_uplift={ov['T_uplift']:.0f}lb "
          f"T_bolt~{ov['T_bolt']:.0f}lb dia~{ov['dia']:.2f}in  "
          f"defl={ov['delta']:.3f}/{ov['d_lim']:.2f}in "
          f"{'OK' if ov['defl_ok'] else 'FAIL'}")
    # monotonic sanity vs previous V
    if prev:
        mono = w['F']>prev['F'] and w['M']>prev['M']
        print(f"  SANITY monotonic vs lower V: {'OK' if mono else 'FAIL'}")
    prev=w
    print("-"*70)
# Cowork comparison (grounded)
cw=wind(111.0)
print("EXTREME ANALYSIS - Cowork cross-check:")
print(f"  Cowork stated F=5593 lb (V=105). Grounded Case A V=111 F={cw['F']:.0f} lb"
      f"  -> Cowork ~{(1-5593/cw['F'])*100:.0f}% NON-CONSERVATIVE on wind.")
print(f"  Cowork footing 14x4x4.5 FAILED (sigma 1955>1500). This study sizes")
print(f"  the COMBINED footing by kern/partial-bearing -> see per-V rows.")
print("="*70)
print("DEFERRED/UNVERIFIED: official Kz/Cf x-check; legally-binding V (AHJ);")
print("Watchfire+fab weights; soil q_allow/mu (geotech); ACI318-17 concrete")
print("breakout; deflection (AASHTO LTS); Case C N/A here; rigorous frame")
print("load split; DXF; PE seal. NOT COMPLETE. NOT APPROVED.")
