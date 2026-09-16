"""
SENTINEL — verification scheduling under freshness decay.

When there are more claims than capacity to check them, which one should be verified next?
This package models each claim as a Beta belief that decays toward its class prior as it ages,
treats free feed evidence and costly verification as different channels, and schedules the next
verification by the expected reduction in *decision* loss per unit cost. Baselines that sort by
score, by staleness, by entropy or at random run on the same simulated world for comparison.

Simulation only. No probes, scans or network access of any kind.
"""
__version__ = "0.1.0a1"
