# Aurex Learning Center

The Learning Center is an in-app reference library for becoming fluent in AI
infrastructure, semiconductor bottlenecks, and supply-chain research language.
It is built into the Aurex dashboard and is also exposed through the dashboard
payload.

## Modules

- AI Compute And Cluster Architecture
- Wafers And Front-End Manufacturing
- Advanced Packaging And Chiplets
- HBM And The Memory Bandwidth Wall
- AI Data Center Networking
- Optics, Lasers, Silicon Photonics, And CPO
- Power, Cooling, And The Rack Constraint
- Serenity-Style Chokepoint Research

Each module includes:

- Plain-English explanation
- Why the layer matters
- Stock research angle
- Hard terms to learn
- Questions to ask while researching
- Video or long-form source links

## Research Loop

Use the library with this loop:

1. Map the AI value chain.
2. Find the physical bottleneck.
3. Identify the obscure supplier or second-order beneficiary.
4. Validate the role with filings, customer language, supplier lists, patents,
   technical docs, job posts, or ecosystem diagrams.
5. Define what would kill the thesis.

## Key Terms

The in-app glossary covers terms like wafer, die, EUV, yield, chiplet,
interposer, substrate, CoWoS, OSAT, TSV, HBM, memory wall, InfiniBand, RoCE,
switch ASIC, laser, transceiver, modulator, photodetector, silicon photonics,
CPO, InP, VRM, CDU, design win, qualification, and chokepoint.

## Data Contract

The content lives in:

```text
src/aurex/learning.py
```

The dashboard payload includes:

```json
{
  "learning_center": {
    "title": "AI Value Chain Learning Center",
    "module_count": 8,
    "glossary_count": 33,
    "modules": [],
    "glossary": []
  }
}
```

The standalone API endpoint is:

```text
GET /api/learning
```
