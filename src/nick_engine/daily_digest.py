import argparse
import html
import json
import os
from dataclasses import dataclass, replace
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Mapping, Optional, Sequence, Type
from zoneinfo import ZoneInfo

from .analyzer import analyze_thesis
from .models import CandidateCompany, Evidence, RankedCandidate, ThesisReport
from .providers import ResearchProvider


TORONTO = ZoneInfo("America/Toronto")


@dataclass(frozen=True)
class ThesisTrack:
    title: str
    thesis: str
    max_market_cap_b: float = None


@dataclass(frozen=True)
class DailyDigest:
    subject: str
    html: str
    text: str
    tickers: tuple = ()


@dataclass(frozen=True)
class RunResult:
    status: str
    message: str


THESIS_TRACKS = (
    ThesisTrack("Optical Networking Bottleneck", "AI data center optical networking bottleneck"),
    ThesisTrack("Memory / HBM Bottleneck", "AI memory bandwidth HBM bottleneck"),
    ThesisTrack(
        "Construction Equipment Demand",
        "construction equipment demand will skyrocket",
        max_market_cap_b=15,
    ),
)

DIGEST_RECIPIENTS = ("marko@advertra.ca", "ikeepitstream@gmail.com")
MIN_AUREX_SCORE = 80
MIN_NICK_SCORE = MIN_AUREX_SCORE
MIN_EXPLOSIVE_SETUP_SCORE = 60
MIN_NEAR_TERM_REASONS = 2
MAX_CANDIDATES_PER_THESIS = 3
DIGEST_HISTORY_PATH = Path(".github/digest-history.json")

ALREADY_RESEARCHED_TICKERS = frozenset(
    {
        "AAOI",
        "ACMR",
        "ADI",
        "AEHR",
        "ALMU",
        "AMAT",
        "AMD",
        "AMKR",
        "ARM",
        "ASX",
        "ASTS",
        "AXTI",
        "BB",
        "BE",
        "CASY",
        "CAT",
        "CBRS",
        "CCJ",
        "CIFR",
        "CIEN",
        "COHR",
        "COPX",
        "CPRX",
        "CRCL",
        "CRDO",
        "CRWD",
        "DELL",
        "DLLL",
        "DRAM",
        "FIX",
        "FN",
        "FWT",
        "GFS",
        "GLW",
        "GOOG",
        "GOOGL",
        "HLIT",
        "HIMX",
        "IE",
        "INTC",
        "IREN",
        "JBL",
        "LITE",
        "LNOK",
        "LWLG",
        "MRVL",
        "MU",
        "MULL",
        "NBIS",
        "NOK",
        "NOW",
        "NOWL",
        "NTES",
        "NVTS",
        "ON",
        "ONDS",
        "ONTO",
        "ORCL",
        "OSS",
        "OTGLY",
        "PANW",
        "PDFS",
        "PENG",
        "PL",
        "PLAB",
        "PLTU",
        "POWI",
        "POWL",
        "PUBR",
        "Q",
        "QCOM",
        "RIO",
        "RKLB",
        "RMBS",
        "SEI",
        "SIMO",
        "SITM",
        "SKYT",
        "SMH",
        "SNDK",
        "SNDU",
        "SPHR",
        "STX",
        "SUNB",
        "TATT",
        "TE",
        "TSM",
        "TSEM",
        "TTMI",
        "TTWO",
        "TXN",
        "UEC",
        "URI",
        "URNM",
        "VECO",
        "VIAV",
        "VRT",
        "WDCC",
        "WDCX",
        "WOLF",
    }
)

HIDDEN_GEM_AS_OF = "2026-06-01"


def _evidence(title: str, url: str) -> Evidence:
    return Evidence(title=title, url=url, observed_at=HIDDEN_GEM_AS_OF)


HIDDEN_GEM_COMPANIES = (
    CandidateCompany(
        ticker="TEX",
        name="Terex",
        sector="Industrials",
        industry="Construction Machinery",
        market_cap_b=4.0,
        value_chain_layer="second-order: materials processing and lifting equipment",
        exposure="direct",
        thesis_keywords=("construction", "equipment", "infrastructure", "machinery", "lifting"),
        summary=(
            "Smaller equipment manufacturer with exposure to aerial work platforms, "
            "materials processing, and construction fleet replacement."
        ),
        catalysts=("Fleet replacement cycle", "Infrastructure and materials-processing demand"),
        risks=("Cyclical end markets", "Dealer inventory swings"),
        invalidation_signals=("Orders decline", "Backlog converts at weaker margins"),
        evidence=(
            _evidence("Terex investor relations", "https://investors.terex.com/"),
            _evidence("Terex SEC filings", "https://www.sec.gov/edgar/browse/?CIK=97216"),
        ),
        liquidity="medium",
        risk_flags=("cyclical",),
    ),
    CandidateCompany(
        ticker="ALG",
        name="Alamo Group",
        sector="Industrials",
        industry="Industrial and Vegetation Management Equipment",
        market_cap_b=2.0,
        value_chain_layer="second-order: specialty infrastructure equipment",
        exposure="indirect",
        thesis_keywords=("construction", "equipment", "infrastructure", "machinery"),
        summary=(
            "Specialty equipment maker tied to infrastructure maintenance, vegetation "
            "management, and municipal fleet replacement."
        ),
        catalysts=("Municipal infrastructure budgets", "Fleet replacement"),
        risks=("Niche demand", "Input-cost pressure"),
        invalidation_signals=("Municipal orders weaken", "Margins compress"),
        evidence=(
            _evidence("Alamo Group investor relations", "https://www.alamo-group.com/investor-relations/"),
            _evidence("Alamo Group SEC filings", "https://www.sec.gov/edgar/browse/?CIK=897077"),
        ),
        liquidity="medium",
        risk_flags=("niche market",),
    ),
    CandidateCompany(
        ticker="HRI",
        name="Herc Holdings",
        sector="Industrials",
        industry="Equipment Rental",
        market_cap_b=4.0,
        value_chain_layer="second-order: equipment rental",
        exposure="indirect",
        thesis_keywords=("construction", "equipment", "infrastructure", "rental"),
        summary=(
            "Equipment-rental operator that can benefit from construction activity "
            "without requiring contractors to buy machinery outright."
        ),
        catalysts=("Rental utilization", "Infrastructure project demand"),
        risks=("Financing costs", "Rental-rate pressure"),
        invalidation_signals=("Utilization declines", "Rental rates weaken"),
        evidence=(
            _evidence("Herc investor relations", "https://ir.hercrentals.com/"),
            _evidence("Herc SEC filings", "https://www.sec.gov/edgar/browse/?CIK=1364479"),
        ),
        liquidity="medium",
        risk_flags=("leverage sensitivity",),
    ),
    CandidateCompany(
        ticker="ADTN",
        name="Adtran Holdings",
        sector="Photonics",
        industry="Optical Networking",
        market_cap_b=0.6,
        value_chain_layer="L8 connectivity: optical access and transport",
        exposure="direct",
        thesis_keywords=("ai", "data", "center", "optical", "networking", "photonics", "bottleneck"),
        summary=(
            "Smaller optical-networking vendor with access, transport, and fiber "
            "infrastructure exposure when bandwidth spending broadens beyond the obvious leaders."
        ),
        catalysts=("Fiber and optical transport upgrades", "Network capacity spending"),
        risks=("Carrier capex variability", "Small-cap execution risk"),
        invalidation_signals=("Carrier orders weaken", "Gross margins deteriorate"),
        evidence=(
            _evidence("Adtran investor relations", "https://investors.adtran.com/"),
            _evidence("Adtran SEC filings", "https://www.sec.gov/edgar/browse/?CIK=926282"),
        ),
        liquidity="medium",
        risk_flags=("small cap", "carrier capex sensitivity"),
    ),
    CandidateCompany(
        ticker="EXTR",
        name="Extreme Networks",
        sector="Photonics",
        industry="Cloud and Enterprise Networking",
        market_cap_b=2.5,
        value_chain_layer="L8 connectivity: cloud and enterprise networking",
        exposure="indirect",
        thesis_keywords=("ai", "data", "center", "connectivity", "networking", "bottleneck"),
        summary=(
            "Networking vendor that can screen as a second-order beneficiary if "
            "AI-driven bandwidth spending broadens into campus, cloud, and enterprise networks."
        ),
        catalysts=("Network upgrade cycle", "Cloud and enterprise refresh demand"),
        risks=("Competitive switching pressure", "Indirect AI exposure"),
        invalidation_signals=("Bookings weaken", "Channel inventory rises"),
        evidence=(
            _evidence("Extreme Networks investor relations", "https://investor.extremenetworks.com/"),
            _evidence("Extreme Networks SEC filings", "https://www.sec.gov/edgar/browse/?CIK=1078271"),
        ),
        liquidity="medium",
        risk_flags=("indirect exposure",),
    ),
    CandidateCompany(
        ticker="LASR",
        name="nLIGHT",
        sector="Photonics",
        industry="Laser Components",
        market_cap_b=0.5,
        value_chain_layer="L8 adjacency: photonics components",
        exposure="indirect",
        thesis_keywords=("ai", "data", "center", "optical", "photonics", "bottleneck"),
        summary=(
            "Small photonics component company for monitoring when capital rotates "
            "from the obvious optical names into lower-liquidity photonics adjacencies."
        ),
        catalysts=("Photonics sector breadth", "Industrial and defense laser demand"),
        risks=("Indirect data-center exposure", "Low market capitalization"),
        invalidation_signals=("Photonics breadth weakens", "Revenue growth stalls"),
        evidence=(
            _evidence("nLIGHT investor relations", "https://investors.nlight.net/"),
            _evidence("nLIGHT SEC filings", "https://www.sec.gov/edgar/browse/?CIK=1124796"),
        ),
        liquidity="low",
        risk_flags=("small cap", "indirect exposure"),
    ),
    CandidateCompany(
        ticker="FORM",
        name="FormFactor",
        sector="Semiconductors",
        industry="Semiconductor Test and Probe",
        market_cap_b=3.5,
        value_chain_layer="L5 packaging and testing: probe cards",
        exposure="indirect",
        thesis_keywords=("ai", "memory", "bandwidth", "hbm", "semiconductor", "testing", "bottleneck"),
        summary=(
            "Probe-card and test-interface supplier that can benefit when HBM and "
            "advanced packaging bottlenecks push spend into memory test infrastructure."
        ),
        catalysts=("HBM test intensity", "Advanced packaging complexity"),
        risks=("Semicap cyclicality", "Customer concentration"),
        invalidation_signals=("Memory capex weakens", "Probe-card demand slows"),
        evidence=(
            _evidence("FormFactor investor relations", "https://investors.formfactor.com/"),
            _evidence("FormFactor SEC filings", "https://www.sec.gov/edgar/browse/?CIK=1039399"),
        ),
        liquidity="medium",
        risk_flags=("customer concentration",),
    ),
    CandidateCompany(
        ticker="CAMT",
        name="Camtek",
        sector="Semiconductors",
        industry="Semiconductor Inspection and Metrology",
        market_cap_b=4.0,
        value_chain_layer="L5 packaging and testing: inspection and metrology",
        exposure="indirect",
        thesis_keywords=("ai", "memory", "bandwidth", "hbm", "semiconductor", "packaging", "bottleneck"),
        summary=(
            "Inspection and metrology supplier tied to advanced packaging, where "
            "HBM and AI accelerators increase process complexity."
        ),
        catalysts=("Advanced packaging demand", "HBM manufacturing complexity"),
        risks=("Semicap multiple compression", "Order cyclicality"),
        invalidation_signals=("Advanced packaging orders slow", "Backlog declines"),
        evidence=(
            _evidence("Camtek investor relations", "https://www.camtek.com/investors/"),
            _evidence("Camtek SEC filings", "https://www.sec.gov/edgar/browse/?CIK=1109138"),
        ),
        liquidity="medium",
        risk_flags=("semicap cyclicality",),
    ),
    CandidateCompany(
        ticker="MRAM",
        name="Everspin Technologies",
        sector="Semiconductors",
        industry="Specialty Memory",
        market_cap_b=0.1,
        value_chain_layer="L6 memory: specialty memory",
        exposure="indirect",
        thesis_keywords=("ai", "memory", "bandwidth", "semiconductor", "bottleneck"),
        summary=(
            "Micro-cap specialty memory name to monitor only as a high-risk memory "
            "breadth play, not as a direct HBM leader."
        ),
        catalysts=("Memory sector breadth", "Specialty memory design wins"),
        risks=("Micro-cap liquidity", "Indirect HBM exposure"),
        invalidation_signals=("Design wins fail to convert", "Cash burn rises"),
        evidence=(
            _evidence("Everspin investor relations", "https://investor.everspin.com/"),
            _evidence("Everspin SEC filings", "https://www.sec.gov/edgar/browse/?CIK=1438423"),
        ),
        liquidity="low",
        risk_flags=("micro cap", "indirect exposure"),
    ),
    CandidateCompany(
        ticker="CALX",
        name="Calix",
        sector="Photonics",
        industry="Broadband Access Platforms",
        market_cap_b=2.5,
        value_chain_layer="L8 connectivity: fiber access and cloud-managed networking",
        exposure="indirect",
        thesis_keywords=("ai", "data", "center", "optical", "networking", "connectivity", "bottleneck"),
        summary=(
            "Fiber access and cloud-managed networking platform that can catch a bid "
            "when optical and broadband infrastructure spending broadens below the obvious names."
        ),
        catalysts=("Fiber upgrade cycle", "Broadband network refresh orders"),
        risks=("Carrier spending variability", "Indirect data-center exposure"),
        invalidation_signals=("Provider capex weakens", "Subscriber platform growth stalls"),
        evidence=(
            _evidence("Calix investor relations", "https://investor-relations.calix.com/"),
            _evidence("Calix SEC filings", "https://www.sec.gov/edgar/browse/?CIK=1406666"),
        ),
        liquidity="medium",
        risk_flags=("carrier capex sensitivity", "indirect exposure"),
    ),
    CandidateCompany(
        ticker="MTSI",
        name="MACOM Technology Solutions",
        sector="Photonics",
        industry="High-Performance Analog and Optical Semiconductors",
        market_cap_b=11.0,
        value_chain_layer="L8 connectivity: optical and high-speed analog components",
        exposure="direct",
        thesis_keywords=("ai", "data", "center", "optical", "photonics", "connectivity", "bottleneck"),
        summary=(
            "Component supplier with optical, RF, and high-speed analog exposure that can "
            "benefit as AI network bandwidth demand pulls money into the component layer."
        ),
        catalysts=("Optical component demand", "Data-center connectivity design wins"),
        risks=("Semiconductor cyclicality", "Defense and telecom mix variability"),
        invalidation_signals=("Datacom orders weaken", "Design-win conversion slows"),
        evidence=(
            _evidence("MACOM investor relations", "https://ir.macom.com/"),
            _evidence("MACOM SEC filings", "https://www.sec.gov/edgar/browse/?CIK=1493594"),
        ),
        liquidity="medium",
        risk_flags=("semiconductor cyclicality",),
    ),
    CandidateCompany(
        ticker="AVNW",
        name="Aviat Networks",
        sector="Photonics",
        industry="Wireless Transport Networking",
        market_cap_b=0.3,
        value_chain_layer="L8 connectivity: transport networking adjacency",
        exposure="indirect",
        thesis_keywords=("data", "center", "networking", "connectivity", "bottleneck", "infrastructure"),
        summary=(
            "Micro-cap transport networking vendor that can screen as a high-risk breadth "
            "name if bandwidth infrastructure spending moves beyond the clean optical leaders."
        ),
        catalysts=("Backhaul upgrade demand", "Network modernization orders"),
        risks=("Micro-cap liquidity", "Telecom capex sensitivity"),
        invalidation_signals=("Bookings weaken", "Carrier spending slows"),
        evidence=(
            _evidence("Aviat investor relations", "https://investors.aviatnetworks.com/"),
            _evidence("Aviat SEC filings", "https://www.sec.gov/edgar/browse/?CIK=1377789"),
        ),
        liquidity="low",
        risk_flags=("micro cap", "carrier capex sensitivity"),
    ),
    CandidateCompany(
        ticker="OCC",
        name="Optical Cable",
        sector="Photonics",
        industry="Fiber Optic Cable and Connectivity",
        market_cap_b=0.03,
        value_chain_layer="L8 connectivity: fiber optic cable and components",
        exposure="direct",
        thesis_keywords=("data", "center", "optical", "networking", "connectivity", "photonics", "bottleneck"),
        summary=(
            "Tiny fiber-optic cable and connectivity supplier that belongs only in the "
            "high-risk breadth bucket when optical infrastructure demand gets speculative."
        ),
        catalysts=("Fiber infrastructure orders", "Optical connectivity breadth"),
        risks=("Very low liquidity", "Micro-cap execution risk"),
        invalidation_signals=("Revenue growth stalls", "Volume fails to confirm the move"),
        evidence=(
            _evidence("Optical Cable investor relations", "https://www.occfiber.com/investor-relations/"),
            _evidence("Optical Cable SEC filings", "https://www.sec.gov/edgar/browse/?CIK=1000230"),
        ),
        liquidity="low",
        risk_flags=("micro cap", "low liquidity"),
    ),
    CandidateCompany(
        ticker="SMTC",
        name="Semtech",
        sector="Photonics",
        industry="Signal Integrity and Connectivity Semiconductors",
        market_cap_b=4.0,
        value_chain_layer="L8 connectivity: signal integrity and high-speed links",
        exposure="indirect",
        thesis_keywords=("ai", "data", "center", "connectivity", "networking", "semiconductor", "bottleneck"),
        summary=(
            "Connectivity semiconductor name that can participate when the market looks "
            "past optical module leaders and into signal-integrity suppliers."
        ),
        catalysts=("Data-center connectivity refresh", "Signal integrity demand"),
        risks=("Debt and integration risk", "Mixed end-market exposure"),
        invalidation_signals=("Connectivity orders slow", "Balance-sheet pressure rises"),
        evidence=(
            _evidence("Semtech investor relations", "https://investors.semtech.com/"),
            _evidence("Semtech SEC filings", "https://www.sec.gov/edgar/browse/?CIK=88941"),
        ),
        liquidity="medium",
        risk_flags=("balance sheet risk", "indirect exposure"),
    ),
    CandidateCompany(
        ticker="PLUS",
        name="ePlus",
        sector="Photonics",
        industry="Technology Solutions and Networking",
        market_cap_b=2.0,
        value_chain_layer="L8/L9 adjacency: enterprise networking deployment",
        exposure="indirect",
        thesis_keywords=("ai", "data", "center", "networking", "connectivity", "infrastructure", "bottleneck"),
        summary=(
            "Smaller IT solutions provider with networking and data-center deployment exposure; "
            "useful as a second-order breadth read when enterprise AI infrastructure spend broadens."
        ),
        catalysts=("Enterprise network refresh", "Data-center infrastructure orders"),
        risks=("Reseller margin pressure", "Indirect AI exposure"),
        invalidation_signals=("Product backlog declines", "Gross margins weaken"),
        evidence=(
            _evidence("ePlus investor relations", "https://www.eplus.com/investors"),
            _evidence("ePlus SEC filings", "https://www.sec.gov/edgar/browse/?CIK=1022408"),
        ),
        liquidity="medium",
        risk_flags=("indirect exposure",),
    ),
    CandidateCompany(
        ticker="ICHR",
        name="Ichor Holdings",
        sector="Semiconductors",
        industry="Semiconductor Equipment Subsystems",
        market_cap_b=1.0,
        value_chain_layer="L4 equipment: fluid delivery subsystems",
        exposure="indirect",
        thesis_keywords=("ai", "semiconductor", "equipment", "advanced", "packaging", "hbm", "bottleneck"),
        summary=(
            "Small semicap subsystem supplier that can re-rate when wafer-fab and "
            "advanced-node equipment orders recover under AI capacity demand."
        ),
        catalysts=("Semicap order recovery", "Advanced-node capacity additions"),
        risks=("Customer concentration", "Semicap cycle timing"),
        invalidation_signals=("Backlog declines", "WFE spending rolls over"),
        evidence=(
            _evidence("Ichor investor relations", "https://ir.ichorsystems.com/"),
            _evidence("Ichor SEC filings", "https://www.sec.gov/edgar/browse/?CIK=1652535"),
        ),
        liquidity="medium",
        risk_flags=("customer concentration", "semicap cyclicality"),
    ),
    CandidateCompany(
        ticker="ACLS",
        name="Axcelis Technologies",
        sector="Semiconductors",
        industry="Ion Implantation Equipment",
        market_cap_b=4.0,
        value_chain_layer="L4 equipment: ion implantation",
        exposure="indirect",
        thesis_keywords=("ai", "semiconductor", "equipment", "memory", "hbm", "bottleneck"),
        summary=(
            "Ion-implant equipment supplier that can screen as a smaller semicap torque "
            "name when AI-driven capacity spend rotates down into equipment."
        ),
        catalysts=("Equipment order recovery", "Power and memory capacity additions"),
        risks=("Power semiconductor cycle", "Order lumpiness"),
        invalidation_signals=("Bookings weaken", "Customer capex delays"),
        evidence=(
            _evidence("Axcelis investor relations", "https://investor.axcelis.com/"),
            _evidence("Axcelis SEC filings", "https://www.sec.gov/edgar/browse/?CIK=1113232"),
        ),
        liquidity="medium",
        risk_flags=("semicap cyclicality",),
    ),
    CandidateCompany(
        ticker="MKSI",
        name="MKS Instruments",
        sector="Semiconductors",
        industry="Semiconductor Process Control Subsystems",
        market_cap_b=8.0,
        value_chain_layer="L4 equipment: process control and photonics subsystems",
        exposure="indirect",
        thesis_keywords=("ai", "semiconductor", "equipment", "photonics", "advanced", "packaging", "bottleneck"),
        summary=(
            "Process-control and photonics subsystem supplier that can benefit when "
            "advanced manufacturing complexity pulls spend into semicap suppliers."
        ),
        catalysts=("Advanced manufacturing demand", "Semicap and photonics recovery orders"),
        risks=("Leverage from prior acquisition", "Cyclical end markets"),
        invalidation_signals=("Semicap recovery stalls", "Debt paydown disappoints"),
        evidence=(
            _evidence("MKS investor relations", "https://investor.mks.com/"),
            _evidence("MKS SEC filings", "https://www.sec.gov/edgar/browse/?CIK=1049502"),
        ),
        liquidity="medium",
        risk_flags=("balance sheet risk", "semicap cyclicality"),
    ),
    CandidateCompany(
        ticker="COHU",
        name="Cohu",
        sector="Semiconductors",
        industry="Semiconductor Test Equipment",
        market_cap_b=1.5,
        value_chain_layer="L5 packaging and testing: semiconductor test handlers",
        exposure="indirect",
        thesis_keywords=("ai", "semiconductor", "testing", "memory", "hbm", "advanced", "packaging", "bottleneck"),
        summary=(
            "Smaller test-equipment supplier positioned around semiconductor test intensity; "
            "the angle is higher complexity as AI chips, memory, and advanced packages scale."
        ),
        catalysts=("Test intensity growth", "Advanced package and memory test demand"),
        risks=("Cyclical test demand", "Customer spending delays"),
        invalidation_signals=("Orders decline", "Utilization weakens"),
        evidence=(
            _evidence("Cohu investor relations", "https://investors.cohu.com/"),
            _evidence("Cohu SEC filings", "https://www.sec.gov/edgar/browse/?CIK=21535"),
        ),
        liquidity="medium",
        risk_flags=("semicap cyclicality",),
    ),
    CandidateCompany(
        ticker="AEIS",
        name="Advanced Energy Industries",
        sector="Semiconductors",
        industry="Precision Power Conversion",
        market_cap_b=4.0,
        value_chain_layer="L4/L7 equipment and power: precision power delivery",
        exposure="indirect",
        thesis_keywords=("ai", "semiconductor", "equipment", "power", "advanced", "packaging", "bottleneck"),
        summary=(
            "Precision power supplier tied to semiconductor tools and data-center power needs; "
            "a second-order beneficiary if AI capex keeps stressing power and equipment layers."
        ),
        catalysts=("Semicap power demand", "Data-center power conversion orders"),
        risks=("Industrial cyclicality", "Indirect AI exposure"),
        invalidation_signals=("Order recovery fades", "Margins compress"),
        evidence=(
            _evidence("Advanced Energy investor relations", "https://ir.advancedenergy.com/"),
            _evidence("Advanced Energy SEC filings", "https://www.sec.gov/edgar/browse/?CIK=927003"),
        ),
        liquidity="medium",
        risk_flags=("indirect exposure",),
    ),
    CandidateCompany(
        ticker="KLIC",
        name="Kulicke and Soffa",
        sector="Semiconductors",
        industry="Semiconductor Assembly Equipment",
        market_cap_b=2.5,
        value_chain_layer="L5 packaging and testing: assembly equipment",
        exposure="indirect",
        thesis_keywords=("ai", "semiconductor", "advanced", "packaging", "hbm", "testing", "bottleneck"),
        summary=(
            "Assembly-equipment supplier that can matter if money rotates from HBM "
            "leaders into packaging and assembly bottleneck beneficiaries."
        ),
        catalysts=("Advanced packaging adoption", "Assembly equipment order recovery"),
        risks=("Packaging cycle timing", "China exposure"),
        invalidation_signals=("Bookings fail to recover", "Advanced packaging demand slows"),
        evidence=(
            _evidence("Kulicke and Soffa investor relations", "https://investor.kns.com/"),
            _evidence("Kulicke and Soffa SEC filings", "https://www.sec.gov/edgar/browse/?CIK=56978"),
        ),
        liquidity="medium",
        risk_flags=("semicap cyclicality",),
    ),
    CandidateCompany(
        ticker="UCTT",
        name="Ultra Clean Holdings",
        sector="Semiconductors",
        industry="Semiconductor Subsystems and Services",
        market_cap_b=1.5,
        value_chain_layer="L4 equipment: critical subsystems and services",
        exposure="indirect",
        thesis_keywords=("ai", "semiconductor", "equipment", "advanced", "packaging", "memory", "bottleneck"),
        summary=(
            "Semicap subsystem and services supplier with small-cap torque to wafer-fab "
            "equipment recovery and AI capacity additions."
        ),
        catalysts=("WFE order recovery", "Critical subsystem demand"),
        risks=("Customer concentration", "Semicap cyclicality"),
        invalidation_signals=("Major customer orders weaken", "Service demand slows"),
        evidence=(
            _evidence("Ultra Clean investor relations", "https://uct.com/investors/"),
            _evidence("Ultra Clean SEC filings", "https://www.sec.gov/edgar/browse/?CIK=1275014"),
        ),
        liquidity="medium",
        risk_flags=("customer concentration", "semicap cyclicality"),
    ),
    CandidateCompany(
        ticker="VICR",
        name="Vicor",
        sector="Semiconductors",
        industry="Power Modules",
        market_cap_b=2.0,
        value_chain_layer="L7 power semiconductors: high-density power modules",
        exposure="indirect",
        thesis_keywords=("ai", "data", "center", "power", "semiconductor", "memory", "bottleneck"),
        summary=(
            "High-density power module supplier that can become relevant when AI racks "
            "push power-delivery constraints into the tradeable bottleneck list."
        ),
        catalysts=("AI rack power density demand", "Power module design wins"),
        risks=("Customer concentration", "Patent and execution risk"),
        invalidation_signals=("Design-win momentum slows", "Revenue growth fails to recover"),
        evidence=(
            _evidence("Vicor investor relations", "https://investor.vicorpower.com/"),
            _evidence("Vicor SEC filings", "https://www.sec.gov/edgar/browse/?CIK=751978"),
        ),
        liquidity="medium",
        risk_flags=("customer concentration",),
    ),
    CandidateCompany(
        ticker="DIOD",
        name="Diodes",
        sector="Semiconductors",
        industry="Analog and Discrete Semiconductors",
        market_cap_b=3.0,
        value_chain_layer="L7 power and analog semiconductors",
        exposure="indirect",
        thesis_keywords=("ai", "semiconductor", "power", "data", "center", "memory", "bottleneck"),
        summary=(
            "Analog and discrete semiconductor supplier that screens as a smaller "
            "power-adjacent beneficiary if AI infrastructure demand broadens into supporting silicon."
        ),
        catalysts=("Power and analog order recovery", "Data-center support silicon demand"),
        risks=("Broad industrial cycle", "Indirect AI exposure"),
        invalidation_signals=("Channel inventory rises", "Bookings weaken"),
        evidence=(
            _evidence("Diodes investor relations", "https://investor.diodes.com/"),
            _evidence("Diodes SEC filings", "https://www.sec.gov/edgar/browse/?CIK=29002"),
        ),
        liquidity="medium",
        risk_flags=("indirect exposure",),
    ),
    CandidateCompany(
        ticker="PI",
        name="Impinj",
        sector="Semiconductors",
        industry="RAIN RFID Semiconductors",
        market_cap_b=3.0,
        value_chain_layer="L2/L7 edge connectivity silicon adjacency",
        exposure="indirect",
        thesis_keywords=("ai", "semiconductor", "connectivity", "data", "infrastructure", "bottleneck"),
        summary=(
            "RFID semiconductor platform with data-capture infrastructure exposure; "
            "not an HBM name, but a smaller semiconductor momentum candidate when breadth expands."
        ),
        catalysts=("Platform adoption", "Semiconductor breadth and fresh orders"),
        risks=("Indirect thesis fit", "Valuation sensitivity"),
        invalidation_signals=("Endpoint IC demand weakens", "Platform adoption slows"),
        evidence=(
            _evidence("Impinj investor relations", "https://investors.impinj.com/"),
            _evidence("Impinj SEC filings", "https://www.sec.gov/edgar/browse/?CIK=1114995"),
        ),
        liquidity="medium",
        risk_flags=("indirect exposure",),
    ),
    CandidateCompany(
        ticker="NVMI",
        name="Nova",
        sector="Semiconductors",
        industry="Semiconductor Metrology",
        market_cap_b=6.0,
        value_chain_layer="L5 packaging and testing: metrology and process control",
        exposure="indirect",
        thesis_keywords=("ai", "semiconductor", "metrology", "advanced", "packaging", "hbm", "bottleneck"),
        summary=(
            "Metrology supplier tied to process complexity in advanced nodes and packaging; "
            "a clean second-order screen when AI manufacturing bottlenecks get bid."
        ),
        catalysts=("Metrology intensity growth", "Advanced packaging and node complexity"),
        risks=("Semicap multiple compression", "Order cyclicality"),
        invalidation_signals=("Metrology orders slow", "Advanced-node capex weakens"),
        evidence=(
            _evidence("Nova investor relations", "https://www.novami.com/investors/"),
            _evidence("Nova SEC filings", "https://www.sec.gov/edgar/browse/?CIK=1109345"),
        ),
        liquidity="medium",
        risk_flags=("semicap cyclicality",),
    ),
    CandidateCompany(
        ticker="OSK",
        name="Oshkosh",
        sector="Industrials",
        industry="Specialty Vehicles and Access Equipment",
        market_cap_b=7.0,
        value_chain_layer="second-order: access equipment and specialty vehicles",
        exposure="indirect",
        thesis_keywords=("construction", "equipment", "infrastructure", "machinery", "demand"),
        summary=(
            "Specialty vehicle and access-equipment manufacturer with JLG exposure; "
            "a less obvious way to monitor construction equipment and fleet demand."
        ),
        catalysts=("Access equipment demand", "Infrastructure and fleet replacement orders"),
        risks=("Cyclical construction demand", "Defense and specialty vehicle mix"),
        invalidation_signals=("Access equipment orders weaken", "Fleet replacement slows"),
        evidence=(
            _evidence("Oshkosh investor relations", "https://investors.oshkoshcorp.com/"),
            _evidence("Oshkosh SEC filings", "https://www.sec.gov/edgar/browse/?CIK=775158"),
        ),
        liquidity="medium",
        risk_flags=("cyclical",),
    ),
    CandidateCompany(
        ticker="TITN",
        name="Titan Machinery",
        sector="Industrials",
        industry="Equipment Dealer",
        market_cap_b=0.5,
        value_chain_layer="second-order: construction and agriculture equipment dealership",
        exposure="indirect",
        thesis_keywords=("construction", "equipment", "infrastructure", "machinery", "demand"),
        summary=(
            "Equipment dealer with operating torque to machinery demand, used-equipment pricing, "
            "and fleet replacement behavior rather than OEM headline multiple expansion."
        ),
        catalysts=("Equipment replacement cycle", "Construction machinery demand"),
        risks=("Dealer inventory swings", "Agriculture cycle exposure"),
        invalidation_signals=("Inventories rise", "Equipment margins compress"),
        evidence=(
            _evidence("Titan Machinery investor relations", "https://investors.titanmachinery.com/"),
            _evidence("Titan Machinery SEC filings", "https://www.sec.gov/edgar/browse/?CIK=1409171"),
        ),
        liquidity="medium",
        risk_flags=("small cap", "dealer inventory risk"),
    ),
    CandidateCompany(
        ticker="PRIM",
        name="Primoris Services",
        sector="Industrials",
        industry="Infrastructure Construction Services",
        market_cap_b=4.0,
        value_chain_layer="second-order: infrastructure contractor",
        exposure="indirect",
        thesis_keywords=("construction", "equipment", "infrastructure", "demand", "project"),
        summary=(
            "Infrastructure contractor that can benefit from the same project backlog "
            "that pulls construction equipment utilization, rentals, and fleet replacement higher."
        ),
        catalysts=("Infrastructure backlog", "Project award momentum"),
        risks=("Project execution", "Labor and cost inflation"),
        invalidation_signals=("Backlog conversion weakens", "Margins deteriorate"),
        evidence=(
            _evidence("Primoris investor relations", "https://investor.prim.com/"),
            _evidence("Primoris SEC filings", "https://www.sec.gov/edgar/browse/?CIK=1361538"),
        ),
        liquidity="medium",
        risk_flags=("project execution",),
    ),
    CandidateCompany(
        ticker="STRL",
        name="Sterling Infrastructure",
        sector="Industrials",
        industry="Infrastructure and Site Development",
        market_cap_b=5.0,
        value_chain_layer="second-order: site development and infrastructure buildout",
        exposure="indirect",
        thesis_keywords=("construction", "equipment", "infrastructure", "demand", "project"),
        summary=(
            "Infrastructure and site-development contractor with data-center and civil exposure; "
            "a demand-side read-through for equipment utilization and construction intensity."
        ),
        catalysts=("Data-center site work", "Infrastructure backlog and awards"),
        risks=("Execution risk", "Valuation sensitivity after strong runs"),
        invalidation_signals=("Awards slow", "Margins normalize lower"),
        evidence=(
            _evidence("Sterling investor relations", "https://investor.strlco.com/"),
            _evidence("Sterling SEC filings", "https://www.sec.gov/edgar/browse/?CIK=874238"),
        ),
        liquidity="medium",
        risk_flags=("project execution",),
    ),
    CandidateCompany(
        ticker="ROAD",
        name="Construction Partners",
        sector="Industrials",
        industry="Roadway Construction",
        market_cap_b=5.0,
        value_chain_layer="second-order: road construction and materials",
        exposure="indirect",
        thesis_keywords=("construction", "equipment", "infrastructure", "roadbuilding", "demand"),
        summary=(
            "Roadway construction platform that can benefit when public works and roadbuilding "
            "activity drive equipment utilization and asphalt/material demand."
        ),
        catalysts=("Roadbuilding project demand", "Public infrastructure awards"),
        risks=("Weather and project timing", "Materials cost pressure"),
        invalidation_signals=("Bid activity weakens", "Margins compress"),
        evidence=(
            _evidence("Construction Partners investor relations", "https://ir.constructionpartners.net/"),
            _evidence("Construction Partners SEC filings", "https://www.sec.gov/edgar/browse/?CIK=1718227"),
        ),
        liquidity="medium",
        risk_flags=("project timing",),
    ),
    CandidateCompany(
        ticker="LNN",
        name="Lindsay",
        sector="Industrials",
        industry="Infrastructure and Irrigation Equipment",
        market_cap_b=1.5,
        value_chain_layer="second-order: road safety and infrastructure equipment",
        exposure="indirect",
        thesis_keywords=("construction", "equipment", "infrastructure", "machinery", "demand"),
        summary=(
            "Infrastructure and irrigation equipment company with a road-safety segment; "
            "smaller, less crowded, and tied to municipal and infrastructure spend."
        ),
        catalysts=("Infrastructure equipment orders", "Road safety project demand"),
        risks=("Agriculture cycle exposure", "Municipal budget timing"),
        invalidation_signals=("Infrastructure orders weaken", "Dealer demand slows"),
        evidence=(
            _evidence("Lindsay investor relations", "https://www.lindsay.com/usca/en/investor-relations/"),
            _evidence("Lindsay SEC filings", "https://www.sec.gov/edgar/browse/?CIK=836157"),
        ),
        liquidity="medium",
        risk_flags=("niche market",),
    ),
    CandidateCompany(
        ticker="ATKR",
        name="Atkore",
        sector="Industrials",
        industry="Electrical Infrastructure Products",
        market_cap_b=2.5,
        value_chain_layer="second-order: electrical infrastructure for construction",
        exposure="indirect",
        thesis_keywords=("construction", "equipment", "infrastructure", "data", "center", "demand"),
        summary=(
            "Electrical infrastructure products supplier tied to commercial construction, "
            "grid work, and data-center buildouts that can move with infrastructure capex."
        ),
        catalysts=("Data-center electrical demand", "Commercial construction infrastructure orders"),
        risks=("Steel/input pricing", "Nonresidential construction cycle"),
        invalidation_signals=("Electrical product demand weakens", "Margins compress"),
        evidence=(
            _evidence("Atkore investor relations", "https://investors.atkore.com/"),
            _evidence("Atkore SEC filings", "https://www.sec.gov/edgar/browse/?CIK=1666138"),
        ),
        liquidity="medium",
        risk_flags=("input cost sensitivity",),
    ),
    CandidateCompany(
        ticker="IESC",
        name="IES Holdings",
        sector="Industrials",
        industry="Electrical and Infrastructure Services",
        market_cap_b=4.0,
        value_chain_layer="second-order: electrical contracting and infrastructure services",
        exposure="indirect",
        thesis_keywords=("construction", "equipment", "infrastructure", "data", "center", "demand"),
        summary=(
            "Electrical contractor and infrastructure services company with exposure to "
            "data-center and nonresidential buildout, a demand-side cousin of equipment utilization."
        ),
        catalysts=("Data-center electrical project demand", "Infrastructure services backlog"),
        risks=("Project execution", "Labor availability"),
        invalidation_signals=("Backlog growth slows", "Labor costs pressure margins"),
        evidence=(
            _evidence("IES Holdings investor relations", "https://www.ies-co.com/investor-relations"),
            _evidence("IES Holdings SEC filings", "https://www.sec.gov/edgar/browse/?CIK=1048268"),
        ),
        liquidity="medium",
        risk_flags=("project execution",),
    ),
)


def is_toronto_send_hour(now: datetime) -> bool:
    return now.astimezone(TORONTO).hour == 9


def _normalize_tickers(tickers: Sequence[str] = ()) -> frozenset:
    return frozenset(
        str(ticker).strip().upper()
        for ticker in tickers
        if str(ticker).strip()
    )


def _read_digest_history(history_path: Path) -> dict:
    if not history_path.exists():
        return {"version": 1, "sent_tickers": [], "runs": []}
    try:
        history = json.loads(history_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Digest history is invalid JSON: {history_path}") from error
    if not isinstance(history, dict):
        raise ValueError(f"Digest history must be a JSON object: {history_path}")
    history.setdefault("version", 1)
    history.setdefault("sent_tickers", [])
    history.setdefault("runs", [])
    return history


def _sent_history_tickers(history_path: Path) -> frozenset:
    history = _read_digest_history(history_path)
    sent = set(_normalize_tickers(history.get("sent_tickers", ())))
    for run in history.get("runs", ()):
        if isinstance(run, dict):
            sent.update(_normalize_tickers(run.get("tickers", ())))
    return frozenset(sent)


def _excluded_tickers(history_path: Path = None) -> frozenset:
    excluded = set(ALREADY_RESEARCHED_TICKERS)
    if history_path is not None:
        excluded.update(_sent_history_tickers(history_path))
    return frozenset(excluded)


def _history_path(environment: Mapping[str, str] = None, history_path: Path = None) -> Path:
    if history_path is not None:
        return Path(history_path)
    values = environment if environment is not None else os.environ
    configured = values.get("DIGEST_HISTORY_PATH", "")
    if configured:
        return Path(configured)
    return DIGEST_HISTORY_PATH


def _fresh_companies(provider: ResearchProvider, excluded_tickers: Sequence[str] = None) -> tuple:
    excluded = (
        _normalize_tickers(excluded_tickers)
        if excluded_tickers is not None
        else ALREADY_RESEARCHED_TICKERS
    )
    fresh = {}
    for company in tuple(provider.companies()) + HIDDEN_GEM_COMPANIES:
        ticker = company.ticker.upper()
        if ticker not in excluded:
            fresh.setdefault(ticker, company)
    return tuple(fresh.values())


def _default_research_provider(
    environment: Mapping[str, str] = None,
    excluded_tickers: Sequence[str] = None,
) -> ResearchProvider:
    from .fixtures import COMPANIES, ROTATION_SIGNALS
    from .live_provider import LiveResearchProvider
    from .providers import FixtureResearchProvider

    values = environment if environment is not None else os.environ
    configured_provider = (
        values.get("AUREX_RESEARCH_PROVIDER", "")
        or values.get("NICK_RESEARCH_PROVIDER", "")
    ).lower()
    if configured_provider == "fixture":
        return FixtureResearchProvider()
    live_candidates = tuple(
        company
        for company in tuple(COMPANIES) + HIDDEN_GEM_COMPANIES
        if company.ticker.upper()
        not in (
            _normalize_tickers(excluded_tickers)
            if excluded_tickers is not None
            else ALREADY_RESEARCHED_TICKERS
        )
    )
    return LiveResearchProvider(
        base_companies=live_candidates,
        base_rotation_signals=ROTATION_SIGNALS,
    )


def _reports(
    provider: ResearchProvider,
    excluded_tickers: Sequence[str] = None,
) -> Sequence[tuple]:
    companies = _fresh_companies(provider, excluded_tickers=excluded_tickers)
    reports = []
    for track in THESIS_TRACKS:
        report = analyze_thesis(
            track.thesis,
            companies,
            provider.rotation_signals(),
            max_market_cap_b=track.max_market_cap_b,
        )
        high_conviction = tuple(
            candidate
            for candidate in report.candidates
            if candidate.score >= MIN_AUREX_SCORE
            and candidate.setup_score >= MIN_EXPLOSIVE_SETUP_SCORE
            and len(candidate.setup_reasons) >= MIN_NEAR_TERM_REASONS
        )[:MAX_CANDIDATES_PER_THESIS]
        reports.append((track, replace(report, candidates=high_conviction)))
    return tuple(reports)


def _score_breakdown_text(candidate: RankedCandidate) -> str:
    return ", ".join(
        f"{key.replace('_', ' ')} {value:+d}"
        for key, value in candidate.score_breakdown.items()
    )


def _score_color(value: int) -> str:
    if value >= 90:
        return "#16a34a"
    if value >= 75:
        return "#d6a431"
    return "#dc2626"


def _bar(label: str, value: int, maximum: int = 100) -> str:
    width = max(0, min(100, round((value / maximum) * 100)))
    color = _score_color(value)
    return f"""
      <div style="margin:10px 0">
        <div style="display:flex;justify-content:space-between;gap:12px;font-size:12px;color:#555;margin-bottom:5px">
          <span>{html.escape(label)}</span>
          <strong style="color:#111">{value}/{maximum}</strong>
        </div>
        <div style="height:9px;background:#eee5d6;border-radius:999px;overflow:hidden">
          <div style="width:{width}%;height:9px;background:{color};border-radius:999px"></div>
        </div>
      </div>
    """


def _setup_graphic(candidate: RankedCandidate) -> str:
    company = candidate.company
    catalyst_count = min(len(company.catalysts), 4)
    signal_count = min(len(candidate.setup_reasons), 4)
    evidence_count = min(len(company.evidence), 4)
    chips = "".join(
        f"""
        <td style="width:33.33%;padding:8px;border-right:{'1px solid #eadfcb' if label != 'Evidence' else '0'}">
          <div style="font-size:20px;font-weight:700;color:#111">{count}</div>
          <div style="font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:#7a6a52">{label}</div>
        </td>
        """
        for label, count in (
            ("Catalysts", catalyst_count),
            ("Signals", signal_count),
            ("Evidence", evidence_count),
        )
    )
    return f"""
      <section style="background:linear-gradient(135deg,#151515,#2b2418);border-radius:14px;padding:14px;margin:14px 0;color:#fff">
        <div style="display:flex;justify-content:space-between;gap:16px;align-items:center">
          <div>
            <div style="font-size:11px;text-transform:uppercase;letter-spacing:.12em;color:#d6b46a">Setup Dashboard</div>
            <div style="font-size:17px;font-weight:700;margin-top:3px">{html.escape(company.ticker)} explosive-readiness</div>
          </div>
          <div style="text-align:right">
            <div style="font-size:28px;font-weight:800;color:#fff">{candidate.setup_score}</div>
            <div style="font-size:11px;color:#d6b46a">Setup Score</div>
          </div>
        </div>
        <div style="background:#fff;border-radius:12px;padding:12px;margin-top:12px;color:#111">
          {_bar("Thesis Fit", candidate.score)}
          {_bar("Near-Term Setup", candidate.setup_score)}
          <table role="presentation" cellpadding="0" cellspacing="0" style="width:100%;border-collapse:collapse;margin-top:10px;background:#faf7f0;border:1px solid #eadfcb;border-radius:10px;overflow:hidden">
            <tr>{chips}</tr>
          </table>
        </div>
      </section>
    """


def _deep_dive_paragraphs(candidate: RankedCandidate) -> tuple:
    company = candidate.company
    matched_terms = ", ".join(candidate.matched_keywords)
    catalysts = "; ".join(company.catalysts)
    risks = "; ".join(company.risks)
    invalidations = "; ".join(company.invalidation_signals)
    sources = "; ".join(f"{item.title}: {item.url}" for item in company.evidence)
    setup_reasons = "; ".join(candidate.setup_reasons)

    return (
        (
            f"Thesis fit: {company.ticker} scores {candidate.score} with risk "
            f"{candidate.risk_tier}. It maps to {company.value_chain_layer}, with "
            f"{company.exposure} exposure to the thesis through matched terms "
            f"{matched_terms}. score breakdown: {_score_breakdown_text(candidate)}."
        ),
        (
            f"Why it could move soon: Setup score {candidate.setup_score}. "
            f"{setup_reasons}."
        ),
        (
            f"Why it can work: {company.summary} The practical setup is {catalysts}. "
            f"The hidden-gem angle is that this is not the obvious mega-cap expression; "
            f"it is a smaller value-chain beneficiary that can re-rate if money rotates "
            f"from the headline names into the bottleneck layer."
        ),
        (
            f"What kills it: {risks}. The invalidation checklist is {invalidations}. "
            f"Source trail for deeper review: {sources}."
        ),
    )


def _html_candidate(candidate: RankedCandidate) -> str:
    company = candidate.company
    paragraphs = "".join(
        f"<p style=\"margin:10px 0 0;line-height:1.55\">{html.escape(paragraph)}</p>"
        for paragraph in _deep_dive_paragraphs(candidate)
    )
    return f"""
      <article style="border:1px solid #e6e1d8;border-radius:14px;padding:18px 20px;margin:16px 0;background:#fff">
        <div style="display:flex;justify-content:space-between;gap:16px;align-items:flex-start">
          <div>
            <p style="margin:0 0 4px;color:#8a6f3f;font-size:12px;text-transform:uppercase;letter-spacing:.08em">Hidden Gem Candidate</p>
            <h3 style="margin:0;color:#111;font-size:22px">{html.escape(company.ticker)} - {html.escape(company.name)}</h3>
          </div>
          <div style="text-align:right;white-space:nowrap">
            <div style="font-size:24px;font-weight:700;color:#111">{candidate.score}</div>
            <div style="font-size:12px;color:#666">Score</div>
          </div>
        </div>
        <p style="margin:12px 0 0;line-height:1.5">
          <strong>Setup score:</strong> {candidate.setup_score} &nbsp;|&nbsp;
          <strong>Risk:</strong> {candidate.risk_tier} &nbsp;|&nbsp;
          <strong>Exposure:</strong> {html.escape(company.exposure)}<br>
          <strong>Layer:</strong> {html.escape(company.value_chain_layer)}
        </p>
        {_setup_graphic(candidate)}
        {paragraphs}
      </article>
    """


def _text_candidate(candidate: RankedCandidate) -> str:
    company = candidate.company
    paragraphs = "\n\n".join(_deep_dive_paragraphs(candidate))
    return (
        f"{company.ticker} - {company.name} | score {candidate.score} | "
        f"setup score {candidate.setup_score} | risk {candidate.risk_tier}\n"
        f"Layer: {company.value_chain_layer} | exposure: {company.exposure}\n"
        f"{paragraphs}"
    )


def _html_section(track: ThesisTrack, report: ThesisReport) -> str:
    candidates = "".join(_html_candidate(candidate) for candidate in report.candidates)
    return f"""
      <section style="margin:28px 0">
        <h2 style="font-size:24px;margin:0 0 6px;color:#111">{html.escape(track.title)}</h2>
        <p style="margin:0 0 14px;color:#555;line-height:1.5"><strong>Thesis:</strong> {html.escape(track.thesis)}</p>
        {candidates or "<p>No configured candidates matched this thesis.</p>"}
      </section>
    """


def _text_section(track: ThesisTrack, report: ThesisReport) -> str:
    candidates = "\n\n".join(_text_candidate(candidate) for candidate in report.candidates)
    return f"{track.title}\nThesis: {track.thesis}\n\n{candidates or 'No configured candidates matched.'}"


def _selected_tickers(reports: Sequence[tuple]) -> tuple:
    tickers = []
    for _, report in reports:
        for candidate in report.candidates:
            tickers.append(candidate.company.ticker.upper())
    return tuple(dict.fromkeys(tickers))


def _excluded_note(excluded_tickers: Sequence[str] = None) -> str:
    tickers = (
        sorted(_normalize_tickers(excluded_tickers))
        if excluded_tickers is not None
        else sorted(ALREADY_RESEARCHED_TICKERS)
    )
    return (
        "Already researched tickers excluded from candidate output "
        "(including previous digest sends): "
        + ", ".join(tickers)
    )


def _digest_recipients(environment: Mapping[str, str] = None) -> tuple:
    values = environment if environment is not None else os.environ
    configured = values.get("DIGEST_RECIPIENTS", "")
    if not configured:
        return DIGEST_RECIPIENTS
    return tuple(
        recipient.strip()
        for recipient in configured.split(",")
        if recipient.strip()
    )


def build_daily_digest(
    provider: ResearchProvider,
    now: datetime = None,
    excluded_tickers: Sequence[str] = None,
) -> DailyDigest:
    generated_at = (now or datetime.now(timezone.utc)).astimezone(TORONTO)
    reports = _reports(provider, excluded_tickers=excluded_tickers)
    selected_tickers = _selected_tickers(reports)
    date_label = generated_at.strftime("%Y-%m-%d")
    html_sections = "".join(_html_section(track, report) for track, report in reports)
    text_sections = "\n\n---\n\n".join(_text_section(track, report) for track, report in reports)
    notice = (
        "Research watchlist only. This uses public-source live enrichment where available "
        "and remains a research screen, not a buy/sell recommendation."
    )
    excluded_note = _excluded_note(excluded_tickers)
    return DailyDigest(
        subject=f"Aurex Market Research Digest | Hidden Gems | {date_label}",
        html=f"""
        <main style="font-family:Arial,sans-serif;max-width:780px;margin:auto;color:#161616;background:#faf7f0;padding:28px">
          <section style="background:#111;color:#fff;border-radius:18px;padding:24px;margin-bottom:18px">
            <p style="margin:0 0 8px;color:#d6b46a;font-size:12px;text-transform:uppercase;letter-spacing:.1em">Aurex Daily Research Brief</p>
            <h1 style="margin:0;font-size:30px;line-height:1.15">Hidden Gem Stock Research</h1>
            <p style="margin:12px 0 0;color:#ddd">{html.escape(date_label)} | Snapshot: {html.escape(provider.as_of())} | Minimum score: {MIN_AUREX_SCORE} | Setup gate: {MIN_EXPLOSIVE_SETUP_SCORE}</p>
          </section>
          <section style="background:#fff;border:1px solid #e6e1d8;border-radius:14px;padding:16px 18px;margin-bottom:18px">
            <p style="margin:0;line-height:1.5"><strong>{html.escape(notice)}</strong></p>
            <p style="font-size:13px;color:#666;margin:10px 0 0;line-height:1.45">{html.escape(excluded_note)}</p>
          </section>
          {html_sections}
        </main>
        """,
        text=(
            f"Aurex Hidden Gem Stock Research\n{date_label} | Snapshot: {provider.as_of()} | "
            f"Minimum score: {MIN_AUREX_SCORE} | Setup gate: {MIN_EXPLOSIVE_SETUP_SCORE}\n\n"
            f"{notice}\n\n{excluded_note}\n\n{text_sections}\n"
        ),
        tickers=selected_tickers,
    )


def _record_sent_digest(digest: DailyDigest, send_date: date, history_path: Path) -> None:
    tickers = tuple(dict.fromkeys(ticker.upper() for ticker in digest.tickers))
    if not tickers:
        return

    history = _read_digest_history(history_path)
    runs = list(history.get("runs", ()))
    runs.append(
        {
            "sent_date": send_date.isoformat(),
            "subject": digest.subject,
            "tickers": list(tickers),
        }
    )
    sent_tickers = set(_normalize_tickers(history.get("sent_tickers", ())))
    sent_tickers.update(tickers)

    history["version"] = 1
    history["sent_tickers"] = sorted(sent_tickers)
    history["runs"] = runs

    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text(
        json.dumps(history, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def run_daily_digest(
    *,
    now: datetime = None,
    dry_run: bool = False,
    force: bool = False,
    environment: Mapping[str, str] = None,
    output_directory: Path = Path("output/daily-digest"),
    provider: ResearchProvider = None,
    client_class: Type = None,
    history_path: Path = None,
) -> RunResult:
    from .resend_client import ResendClient

    values = environment if environment is not None else os.environ
    resolved_history_path = _history_path(values, history_path)
    excluded = _excluded_tickers(resolved_history_path)
    current_time = now or datetime.now(timezone.utc)
    if not force and not is_toronto_send_hour(current_time):
        return RunResult("skipped", "Skipped: outside Toronto 9 AM hour.")

    research_provider = provider or _default_research_provider(
        environment=environment,
        excluded_tickers=excluded,
    )
    digest = build_daily_digest(
        research_provider,
        current_time,
        excluded_tickers=excluded,
    )
    if dry_run:
        output_directory.mkdir(parents=True, exist_ok=True)
        preview_path = output_directory / "daily-stock-research-preview.html"
        preview_path.write_text(digest.html, encoding="utf-8")
        return RunResult("dry-run", f"Dry run preview written to {preview_path}.")

    if not digest.tickers:
        return RunResult(
            "skipped",
            "Skipped: no fresh high-scoring tickers after history exclusions.",
        )

    sender_class = client_class or ResendClient
    client = sender_class(
        api_key=values.get("RESEND_API_KEY", ""),
        from_email=values.get("RESEND_FROM_EMAIL", ""),
    )
    local_date = current_time.astimezone(TORONTO).date()
    responses = [
        client.send_digest(
            digest,
            to_email=recipient,
            send_date=local_date,
        )
        for recipient in _digest_recipients(values)
    ]
    _record_sent_digest(digest, local_date, resolved_history_path)
    sent_ids = ", ".join(response["id"] for response in responses)
    return RunResult("sent", f"Sent daily research digest: {sent_ids}.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Send the daily market research digest.")
    parser.add_argument("--dry-run", action="store_true", help="Write an HTML preview without sending.")
    parser.add_argument("--force", action="store_true", help="Run outside Toronto's 9 AM hour.")
    parser.add_argument(
        "--output-dir",
        default="output/daily-digest",
        help="Directory for dry-run preview output.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    arguments = build_parser().parse_args(argv)
    result = run_daily_digest(
        dry_run=arguments.dry_run,
        force=arguments.force,
        output_directory=Path(arguments.output_dir),
    )
    print(result.message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
