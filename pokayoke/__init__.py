"""vision-pokayoke: layered machine-vision error-proofing for assembly lines."""
from .inspect import Result, Spec, golden_image, inspect
from .line import Station
from .parts import DEFECTS, render

__all__ = ["DEFECTS", "Result", "Spec", "Station", "golden_image", "inspect", "render"]
