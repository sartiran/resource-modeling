#! /bin/bash

CONFIGS="RelyOnMiniAOD.json:\
         RelyOnMiniAOD.json,Run2024.json:\
         RelyOnMiniAOD.json,Analysis.json,2018changes.json:\
         RelyOnMiniAOD.json,Analysis.json,2018changes.json,Run2024.json:\
         RelyOnMiniAOD.json,Analysis.json,2018changes.json,IntroduceNanoAOD.json:\
         RelyOnMiniAOD.json,Analysis.json,2018changes.json,IntroduceNanoAOD.json,Run2024.json\
"

#CONFIGS="RelyOnMiniAOD.json:\
#         RelyOnMiniAOD.json,Run2024.json:\
#         RelyOnMiniAOD.json,Analysis.json,2018changes.json:\
#
#CONFIGS="RelyOnMiniAOD.json,Analysis.json,2018changes.json:\
#"


rm -rf test_script.out.d
mkdir  test_script.out.d
for config in $(echo $CONFIGS|tr ':' ' ');
do
  hash=$(echo $config|md5sum|awk '{print $1}')
  outdir=test_script.out.d/$hash
  echo $outdir
  mkdir -p $outdir
  echo $config > $outdir/config
  python events.py $config  1>$outdir'/events.out' 2>$outdir'/events.err'
  python cpu.py $config  1>$outdir'/cpu.out' 2>$outdir'/cpu.err'
  python data.py $config 1>$outdir'/data.out' 2>$outdir'/data.err'
  mv *.png tape_samples.json disk_samples.json $outdir/ 
done

