# PCB2 categorical pose labeling

Post-confirmation PCB2 development diagnosis. The image-only method was declared before this task loaded detector outcomes. The agent had prior Stage4 visual knowledge; this is outcome-independent labeling, not a blind prospective study.

The method uses the saved Stage4 board rectangle to find central exterior bright vertical pin ridges at analysis width512. Canonical means a decisive pin cue above the board; reversed_180 means a decisive cue below it. Other/uncertain means the cue is absent or ambiguous. Precise rotation angles are not estimated. No image is rotated, registered or rescored.

All1,101 image IDs were labeled: all1,001 normals are canonical; 90anomalies canonical,5reversed,5uncertain. Automated pin-component counts are ridge fragments rather than a physical count of pins. Confidence is not a calibrated probability.

Image-only visual review covered32systematically selected canonical images (8per split), all5reversed and all5uncertain cases. The reversed group visibly has lower connectors and inverted component-layout asymmetry. All uncertain cases visually retain canonical board layout but lack a decisive vertical connector cue because pins are absent, bent or folded. These five remain uncertain rather than being relabeled using defect-type or outcome knowledge. Hence uncertain is not evidence of noncanonical pose, and analyses must not pool it with reversed as though both denote180-degree reversal. No manual label overrides or classifier refinement occurred.

All1,001normal images being canonical means the dataset cannot estimate a normal false-alarm rate for reversed boards. Pose effects among anomalies are confounded by defect identity and connector damage. Group samples support cue meaning; they do not establish independently measured classifier sensitivity for every source image.
