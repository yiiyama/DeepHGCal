DeepHGCal 
==================

Interface and extention of the DeepJet framework (https://github.com/mstoye/DeepJet) [CMS-AN-17-126] for HGCal reconstruction purposes.

The framework consists of two parts:
1) HGCal ntuple converter (Dependencies: root5.3/6)
2) DNN training/evaluation (Dependencies: DeepJet and all therein).
   Compile DeepJet with CFLAGS+=-DMAXBRANCHLENGTH=2000 