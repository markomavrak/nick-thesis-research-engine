from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class LearningVideo:
    title: str
    source: str
    url: str


@dataclass(frozen=True)
class LearningModule:
    title: str
    plain_english: str
    why_it_matters: str
    stock_research_angle: str
    hard_terms: tuple[str, ...]
    key_questions: tuple[str, ...]
    videos: tuple[LearningVideo, ...]


@dataclass(frozen=True)
class GlossaryTerm:
    term: str
    definition: str
    why_it_matters: str


LEARNING_MODULES = (
    LearningModule(
        title="AI Compute And Cluster Architecture",
        plain_english=(
            "AI compute is not one magic chip. It is thousands of accelerators, memory, "
            "network links, switches, storage, power systems, and software trying to act "
            "like one giant computer."
        ),
        why_it_matters=(
            "The GPU is only valuable when it stays fed with data. Every weak link that "
            "causes idle GPUs becomes a tradeable bottleneck."
        ),
        stock_research_angle=(
            "Start with the cluster architecture, then work backward into suppliers: "
            "accelerators, HBM, networking ASICs, optical links, cables, power delivery, "
            "cooling, and rack integration."
        ),
        hard_terms=("GPU", "Accelerator", "Training", "Inference", "FLOPS", "Utilization"),
        key_questions=(
            "What makes the cluster run faster or cheaper?",
            "Which part causes expensive GPUs to sit idle?",
            "Which supplier is required before hyperscalers can scale the next rack generation?",
        ),
        videos=(
            LearningVideo(
                "GPUs, Networking, and NVIDIA AI Data Centers",
                "YouTube",
                "https://www.youtube.com/watch?v=roEN75ovpsY",
            ),
        ),
    ),
    LearningModule(
        title="Wafers And Front-End Manufacturing",
        plain_english=(
            "A wafer is a polished silicon disk. Fabs print, deposit, etch, clean, inspect, "
            "and repeat hundreds of times until the wafer contains many individual chips."
        ),
        why_it_matters=(
            "Every leading AI chip starts here. EUV tools, process control, metrology, "
            "materials, and yield determine how many usable chips exist."
        ),
        stock_research_angle=(
            "Look for irreplaceable suppliers in lithography, inspection, deposition, "
            "etch, specialty gases, cleanroom systems, metrology, and yield improvement."
        ),
        hard_terms=("Wafer", "Die", "Fab", "Foundry", "Lithography", "EUV", "Yield"),
        key_questions=(
            "Who supplies the tool or material that cannot be substituted quickly?",
            "Is the supplier tied to leading-edge nodes or only mature-node cycles?",
            "Does better yield create immediate economics for TSMC, Nvidia, or memory makers?",
        ),
        videos=(
            LearningVideo(
                "How are Microchips Made? CPU Manufacturing Process Steps",
                "Branch Education",
                "https://www.youtube.com/watch?v=dX9CGRZwD-w",
            ),
            LearningVideo(
                "The Extreme Engineering of ASML's EUV Light Source",
                "Asianometry",
                "https://www.youtube.com/watch?v=5Ge2RcvDlgw",
            ),
        ),
    ),
    LearningModule(
        title="Advanced Packaging And Chiplets",
        plain_english=(
            "Packaging is how finished dies become one usable product. Advanced packaging "
            "places multiple chips, memory stacks, and high-speed bridges extremely close "
            "together so data moves faster and wastes less power."
        ),
        why_it_matters=(
            "AI accelerators need GPU dies and HBM side by side. Packaging capacity and "
            "substrate complexity can bottleneck Nvidia, AMD, Broadcom, and custom ASIC ramps."
        ),
        stock_research_angle=(
            "Track CoWoS-like capacity, substrates, interposers, test sockets, probe cards, "
            "bonding equipment, OSATs, and inspection/metrology suppliers."
        ),
        hard_terms=("Chiplet", "Interposer", "Substrate", "CoWoS", "SoIC", "OSAT", "TSV"),
        key_questions=(
            "Is this company expanding advanced packaging capacity or supplying the expansion?",
            "Does the part sit between AI accelerators and HBM?",
            "Would a packaging shortage delay a flagship AI chip ramp?",
        ),
        videos=(
            LearningVideo(
                "Advanced Packaging Techniques",
                "YouTube",
                "https://www.youtube.com/watch?v=CAKWkOuoWrs",
            ),
            LearningVideo(
                "A Brief History of Semiconductor Packaging",
                "YouTube",
                "https://www.youtube.com/watch?v=nNpuiJitKwk",
            ),
        ),
    ),
    LearningModule(
        title="HBM And The Memory Bandwidth Wall",
        plain_english=(
            "HBM is stacked DRAM placed beside the processor. It gives AI chips a very wide, "
            "short path to memory so huge models can move data fast enough."
        ),
        why_it_matters=(
            "AI compute is often memory-starved. HBM supply, stack height, testing, packaging, "
            "and yield decide how quickly next-generation AI systems can ship."
        ),
        stock_research_angle=(
            "Research memory makers, HBM test suppliers, probe cards, bonding tools, "
            "substrates, thermal materials, and companies that increase bandwidth per watt."
        ),
        hard_terms=("DRAM", "HBM", "HBM3E", "HBM4", "Stack", "Bandwidth", "Memory Wall"),
        key_questions=(
            "Is HBM sold out or capacity constrained?",
            "Which suppliers benefit from higher stack count or harder test requirements?",
            "Does the candidate help memory bandwidth, yield, or thermal management?",
        ),
        videos=(
            LearningVideo(
                "What is High-Bandwidth Memory? HBM vs. GDDR",
                "YouTube",
                "https://www.youtube.com/watch?v=5hqhhLH3nZ8",
            ),
            LearningVideo(
                "What's Different About HBM4",
                "Semiconductor Engineering",
                "https://www.youtube.com/watch?v=ARcbZ5tSdu8",
            ),
        ),
    ),
    LearningModule(
        title="AI Data Center Networking",
        plain_english=(
            "AI clusters need GPUs to communicate constantly. Networking decides whether "
            "the cluster behaves like one machine or a pile of expensive idle chips."
        ),
        why_it_matters=(
            "The bigger the model and cluster, the more bandwidth and lower latency matter. "
            "Switch ASICs, NICs, cables, optical modules, and software stacks become critical."
        ),
        stock_research_angle=(
            "Track InfiniBand, high-speed Ethernet, switch ASICs, retimers, DSPs, linear-drive "
            "optics, cables, NICs, and suppliers named in AI cluster architecture."
        ),
        hard_terms=("InfiniBand", "Ethernet", "RDMA", "RoCE", "Switch ASIC", "NIC", "Latency"),
        key_questions=(
            "Is the supplier tied to scale-up, scale-out, or both?",
            "Does the product lower latency, increase bandwidth, or cut power?",
            "Is it designed into Nvidia, Broadcom, Marvell, Arista, Cisco, or hyperscaler systems?",
        ),
        videos=(
            LearningVideo(
                "AI Datacenter Networks",
                "YouTube",
                "https://www.youtube.com/watch?v=ghf5qySuy_I",
            ),
            LearningVideo(
                "InfiniBand and RoCE",
                "YouTube",
                "https://www.youtube.com/watch?v=eGoP2wPoaEM",
            ),
        ),
    ),
    LearningModule(
        title="Optics, Lasers, Silicon Photonics, And CPO",
        plain_english=(
            "Electrical signals struggle as speeds and distances rise. Optics convert data "
            "into light so AI systems can move more data with less loss and lower power."
        ),
        why_it_matters=(
            "Optical links are becoming a core data-center bottleneck. Co-packaged optics "
            "moves optical engines closer to switch chips to reduce power and increase density."
        ),
        stock_research_angle=(
            "Look for laser suppliers, indium phosphide platforms, silicon photonics, optical "
            "engines, transceivers, modulators, photodetectors, connectors, and CPO partners."
        ),
        hard_terms=("Laser", "Transceiver", "Modulator", "Photodetector", "Silicon Photonics", "CPO", "InP"),
        key_questions=(
            "Is the company supplying the light source, optical engine, connector, or module?",
            "Is it qualified by a major switch, hyperscaler, or AI infrastructure platform?",
            "Does the technology solve bandwidth density or power per bit?",
        ),
        videos=(
            LearningVideo(
                "Co-Packaged Optics for our Connected Future",
                "YouTube",
                "https://www.youtube.com/watch?v=Xt-GY8Pkt6g",
            ),
            LearningVideo(
                "The AI Bandwidth Wall & Co-Packaged Optics",
                "YouTube",
                "https://www.youtube.com/watch?v=G5r2OyCN5_s",
            ),
            LearningVideo(
                "What is Silicon Photonics?",
                "Intel Business",
                "https://www.youtube.com/watch?v=gsTl2qkWnp0",
            ),
        ),
    ),
    LearningModule(
        title="Power, Cooling, And The Rack Constraint",
        plain_english=(
            "AI racks are dense power plants. Electricity must be converted, delivered, "
            "regulated, and cooled before the chips can run at full speed."
        ),
        why_it_matters=(
            "If the rack cannot get enough power or remove enough heat, compute capacity is "
            "stranded. Power modules, liquid cooling, and thermal materials become bottlenecks."
        ),
        stock_research_angle=(
            "Study power semiconductors, voltage regulators, power modules, busbars, liquid "
            "cooling, heat exchangers, pumps, CDU systems, and data-center electrical contractors."
        ),
        hard_terms=("VRM", "Power Module", "Thermal Throttling", "Liquid Cooling", "CDU", "Power Density"),
        key_questions=(
            "Does the product let a rack run more GPUs per square foot?",
            "Is power or cooling named as a limiter by hyperscalers?",
            "Is the supplier attached to Nvidia GB-series racks, hyperscaler buildouts, or data-center electrical work?",
        ),
        videos=(
            LearningVideo(
                "How AI Is Redefining Data Centers: Power, Cooling & High-Speed Networks",
                "YouTube",
                "https://www.youtube.com/watch?v=mV_lRkatZVg",
            ),
        ),
    ),
    LearningModule(
        title="Serenity-Style Chokepoint Research",
        plain_english=(
            "This is the research method for finding overlooked suppliers before the market "
            "understands their role: map the physical value chain, find the hard chokepoint, "
            "validate it with source evidence, then test what would kill the thesis."
        ),
        why_it_matters=(
            "The market usually prices obvious leaders first. The asymmetric opportunity is "
            "often a smaller company whose customer, supplier, or technical role is hidden in filings, slides, job posts, or ecosystem diagrams."
        ),
        stock_research_angle=(
            "Search filings, product pages, patents, conference decks, customer qualification "
            "language, supplier lists, job postings, standards groups, and technical papers for non-obvious validation."
        ),
        hard_terms=("Chokepoint", "Design Win", "Qualification", "Supplier Validation", "Second-Order Beneficiary"),
        key_questions=(
            "What must physically exist before the leader can scale?",
            "Is this supplier hard to replace or just one vendor among many?",
            "What overlooked evidence proves the market should care soon?",
        ),
        videos=(
            LearningVideo(
                "Inside the Mind of Serenity",
                "Singularity Research",
                "https://singularityresearchfund.substack.com/p/inside-the-mind-of-serenity-aleabitoreddit",
            ),
        ),
    ),
)


GLOSSARY = (
    GlossaryTerm("Wafer", "A polished silicon disk that chips are manufactured on.", "No wafer capacity means no finished chips."),
    GlossaryTerm("Die", "One individual chip cut from a processed wafer.", "Yield and die size control supply and cost."),
    GlossaryTerm("Fab", "A chip factory that processes wafers.", "Fabs are the capital-intensive choke point of semiconductor supply."),
    GlossaryTerm("Foundry", "A fab business that manufactures chips designed by other companies.", "TSMC is the key foundry for many leading AI chips."),
    GlossaryTerm("Lithography", "The process of printing circuit patterns onto wafers.", "Smaller, denser chips depend on advanced lithography."),
    GlossaryTerm("EUV", "Extreme ultraviolet lithography for leading-edge chip patterns.", "EUV scarcity gives ASML and its suppliers strategic power."),
    GlossaryTerm("Yield", "The percentage of usable chips produced from a wafer.", "Higher yield increases supply without building a new fab."),
    GlossaryTerm("Reticle", "The mask pattern used during lithography.", "Reticle handling and inspection are critical for defect control."),
    GlossaryTerm("Chiplet", "A smaller chip block combined with other blocks in one package.", "Chiplets make large AI systems manufacturable and modular."),
    GlossaryTerm("Interposer", "A bridge layer connecting chips and memory inside a package.", "It enables high-bandwidth links between GPU dies and HBM."),
    GlossaryTerm("Substrate", "The package base that routes power and signals to the board.", "Advanced substrates can become a packaging bottleneck."),
    GlossaryTerm("CoWoS", "TSMC's chip-on-wafer-on-substrate advanced packaging family.", "It is central to many AI accelerator plus HBM packages."),
    GlossaryTerm("OSAT", "Outsourced semiconductor assembly and test company.", "OSATs handle packaging and test capacity outside foundries."),
    GlossaryTerm("TSV", "Through-silicon via, a vertical connection through silicon.", "TSVs let HBM stacks move data vertically at high bandwidth."),
    GlossaryTerm("HBM", "High-bandwidth memory, stacked DRAM placed close to processors.", "AI chips need HBM to avoid starving compute engines."),
    GlossaryTerm("HBM3E", "Enhanced third-generation HBM.", "It is a current-generation bandwidth and supply constraint."),
    GlossaryTerm("HBM4", "Next-generation HBM standard with more bandwidth.", "The transition changes suppliers, test needs, and packaging complexity."),
    GlossaryTerm("Memory Wall", "The point where compute is limited by data movement, not math.", "The market pays for anything that breaks this wall."),
    GlossaryTerm("InfiniBand", "A low-latency, high-bandwidth networking fabric.", "It is important for large AI training clusters."),
    GlossaryTerm("RoCE", "RDMA over Converged Ethernet.", "It helps Ethernet compete in AI cluster networking."),
    GlossaryTerm("Switch ASIC", "A custom chip inside high-speed network switches.", "Switch silicon defines cluster bandwidth and latency."),
    GlossaryTerm("Laser", "A precise light source used in optical communication.", "Lasers are the starting point for moving data as light."),
    GlossaryTerm("Transceiver", "A module that converts electrical data to optical data and back.", "AI data centers consume huge numbers of high-speed transceivers."),
    GlossaryTerm("Modulator", "A device that encodes data onto light.", "Better modulators improve speed and power efficiency."),
    GlossaryTerm("Photodetector", "A device that converts light back into an electrical signal.", "It completes the receive side of an optical link."),
    GlossaryTerm("Silicon Photonics", "Using silicon chips to route and process light.", "It can scale optical links with semiconductor manufacturing methods."),
    GlossaryTerm("CPO", "Co-packaged optics, placing optics close to switch chips.", "It attacks power and bandwidth limits in next-generation AI networks."),
    GlossaryTerm("InP", "Indium phosphide, a compound semiconductor used in lasers and photonics.", "InP can be a material chokepoint in optical systems."),
    GlossaryTerm("VRM", "Voltage regulator module.", "VRMs deliver stable power to hungry AI processors."),
    GlossaryTerm("CDU", "Coolant distribution unit for liquid-cooled systems.", "Liquid cooling infrastructure becomes mandatory as rack density rises."),
    GlossaryTerm("Design Win", "A customer chooses a supplier's part for a product platform.", "Design wins can convert into years of revenue if volume ramps."),
    GlossaryTerm("Qualification", "Customer testing and approval before a part can ship in volume.", "Qualification is often the hidden proof before revenue appears."),
    GlossaryTerm("Chokepoint", "A hard-to-replace supply-chain node that blocks scale.", "Chokepoints create pricing power and asymmetric stock setups."),
)


def learning_payload() -> dict:
    return {
        "title": "AI Value Chain Learning Center",
        "subtitle": (
            "Aurex reference library for learning the language of AI bottlenecks, "
            "semiconductor manufacturing, packaging, HBM, optics, power, and supply-chain research."
        ),
        "module_count": len(LEARNING_MODULES),
        "glossary_count": len(GLOSSARY),
        "featured_terms": ("Wafer", "Packaging", "HBM", "CPO", "Laser", "Interposer", "TSV", "Chokepoint"),
        "research_loop": (
            "Map the value chain -> find the physical bottleneck -> identify the obscure supplier -> "
            "validate with filings/customer evidence -> define what would kill the thesis."
        ),
        "modules": [asdict(module) for module in LEARNING_MODULES],
        "glossary": [asdict(term) for term in GLOSSARY],
    }
