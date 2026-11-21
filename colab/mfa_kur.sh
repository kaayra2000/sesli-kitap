#!/usr/bin/env bash
# Montreal Forced Aligner'ı arka planda kurar (conda-forge, micromamba). Seslendirmeyi bekletmemek için ayrı başlatılır:
#   !nohup bash /content/mfa_kur.sh > /content/mfa_kur.log 2>&1 &
set -u
[[ -x /content/mfa/bin/mfa ]] && /content/mfa/bin/mfa version >/dev/null 2>&1 && { echo "MFA HAZIR"; exit 0; }
MM=/content/micromamba
mkdir -p $MM && [[ -x $MM/bin/micromamba ]] || curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xj -C $MM bin/micromamba
rm -rf /content/mfa
$MM/bin/micromamba create -y -p /content/mfa --override-channels -c conda-forge python=3.11 montreal-forced-aligner librosa pysoundfile
export PATH=/content/mfa/bin:$PATH
mfa model download acoustic turkish_mfa && mfa model download g2p turkish_mfa && echo "MFA HAZIR"
