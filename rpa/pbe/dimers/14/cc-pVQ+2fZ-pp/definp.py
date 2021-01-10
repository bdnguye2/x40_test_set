#!/usr/bin/python
from math import *
import os
import re
import time
import sys

#---------------------------------------------------------------------
# Simple TM job preparation.
#---------------------------------------------------------------------

######################################################################
# Define functions
######################################################################
# Write input for define
def writedef(hfound,nshls,definp,method,struct,scfparams,ghosts):
  filinp = open(definp,'w')
  filinp.write('\n')
  filinp.write('\n')
  filinp.write('a coord\n')
  filinp.write('*\n')
  filinp.write('no\n')
  if(struct['nbo']==1 and len(struct['bodies'][0])==1):
    print 'atom found'
    print len(struct['bodies'][0])
    filinp.write('no\n')
  filinp.write('b all '+method['basis']+'\n')
  #filinp.write('b "br" cc-pV(Q+2f)Z-PP\n')
  # If core weighted dunning basis AND H atoms
  regexp = re.compile('pwCV')
  if regexp.search(method['basis']) and hfound:
    filinp.write('\n')
    basstring=regexp.sub('pV',method['basis'])
    filinp.write('b "h"'+basstring+'\n')

  #Take care that the atoms string is no longer than 80 or so.
  #If longer, there are I/O problems. A simply strategy is to
  #apply the charge to each ghost atom separately.
  if ghosts:
    for ghost in ghosts:
      ghostbody=struct['bodies'][ghost]

      print ghostbody

      for at in ghostbody:
        filinp.write('c '+str(at)+' 0\n')
  filinp.write('*\n')
  filinp.write('eht\n')
  filinp.write('y\n')
  filinp.write(str(struct['charge'])+'\n')
  if(struct['nbo']==1 and len(struct['bodies'][0])==1):
    filinp.write('n\n')
  filinp.write('y\n')
  if[nshls==2]:
    filinp.write('n\n')
  if method['dft']:
    filinp.write('dft\n')
    filinp.write('on\n')
    filinp.write('func '+method['dftfunc']+'\n')
    filinp.write('grid '+scfparams['dftgrid']+'\n')
    filinp.write('*\n')
  if scfparams['rij']:
    filinp.write('ri\n')
    filinp.write('on\n')
    filinp.write('m 5000\n')
    filinp.write('*\n')
  if scfparams['dsp']:
    filinp.write('dsp\n')
    filinp.write('bj\n')
    filinp.write('*\n')
  if method['rpa']:
    filinp.write('cc\n')
    if method['freeze']:
      filinp.write('freeze\n')
      filinp.write('*\n')
    filinp.write('cbas\n')
    filinp.write('*\n')
    filinp.write('*\n')
  filinp.write('*\n')
  filinp.close()

# Post-modify control    
def modcon(filcon,method,scfparams):
  filinp=open(filcon,'r')
  # For easiness and because control is not that big, read all lines
  vcontrol=filinp.readlines()
  filinp.close()

  # Add new options in the beginning of control
  if method['rpa']:
    if (method['rpagrad'] or method['geo']):
      vcontrol.insert(0,'  rpagrad\n')
    vcontrol.insert(0,'  npoints '+scfparams['rpagrid']+'\n')
    vcontrol.insert(0,'$rirpa\n')

  # Search options and modify them, could be done smarter if scfparams
  # would contain only params to be changed now. Then we could make a
  # convenient loop.
  keystrings =['$scfconv','$denconv','$scftol','$scfiterlimit','$maxcor','$disp4']
  datastrings=[scfparams['scfconv'],scfparams['denconv'],scfparams['scftol'], \
              scfparams['scfiterlimit'],scfparams['maxcor'],'']
  regstrings =['[$]scfconv','[$]denconv','[$]scftol','[$]scfiterlimit',       \
              '[$]maxcor','[$]disp3 bj']

  ii=-1
  for regstr in regstrings:
    ii = ii+1
    vcontrolnew=[]
    regexp=re.compile(regstr)
    for line in vcontrol:
      if regexp.search(line):
        #write new line
        vcontrolnew.append(keystrings[ii]+' '+datastrings[ii]+'\n')
      else:
        #write old line
        vcontrolnew.append(line)
    vcontrol=vcontrolnew[:]
 
  #then replace the entire file with the new vcontrol
  filinp=open(filcon,'w')
  for line in vcontrol:
    filinp.write(line)
  filinp.close()

# Modify a runjob template for your needs
def modjob(runjob,jobparams,method,scfparams):
  #Modify parameters in the runjob
  filinp=open(runjob,'r')
  vjob=filinp.readlines()
  filinp.close()

  # Title
  regexp=re.compile('^#PBS -N')
  vjobnew=[]
  for line in vjob:
    if regexp.search(line):
      vjobnew.append('#PBS -N '+jobparams['jobtitle']+'\n')
    else:
      vjobnew.append(line)
  vjob=vjobnew[:]

  # Time Queue
  regexp=re.compile('^#PBS -q')
  vjobnew=[]
  for line in vjob:
    if regexp.search(line):
      vjobnew.append('#PBS -q '+jobparams['jobtime']+'\n')
    else:
      vjobnew.append(line)
  vjob=vjobnew[:]

  # Memory and Disc space
  regexp=re.compile('^#PBS -l')
  vjobnew=[]
  for line in vjob:
    if regexp.search(line):
      vjobnew.append('#PBS -l nodes=1:ppn=1,mem='+jobparams['jobmem']+ \
                     'mb,file='+jobparams['jobdisc']+'gb\n')
    else:
      vjobnew.append(line)
  vjob=vjobnew[:]

  # TM Version
  regexp=re.compile('^export TURBODIR=')
  vjobnew=[]
  for line in vjob:
    if regexp.search(line):
      vjobnew.append('export TURBODIR='+jobparams['tmversion']+'\n')
    else:
      vjobnew.append(line)
  vjob=vjobnew[:]

  # TM Version (Image)
  regexp=re.compile('^export TURBOIMG=')
  vjobnew=[]
  for line in vjob:
    if regexp.search(line):
      vjobnew.append('export TURBOIMG='+jobparams['tmversion']+'\n')
    else:
      vjobnew.append(line)
  vjob=vjobnew[:]

  # Execution Commands
  if method['geo']:
    regexp=re.compile('^#BEGIN EXECUTION SECTION')
    vjobnew=[]
    for line in vjob:
      if regexp.search(line):
        vjobnew.append(line)
        if method['rpa']:
          vjobnew.append('jobex -ri -level rirpa -c 200 -energy 6 -gcart 3'+'\n')
        elif method['dft']:
          vjobnew.append('jobex -ri -c 200 -energy 6 -gcart 3'+'\n')
        else:
          print 'Something wrong here'
          exit()
      else:
        vjobnew.append(line)
    vjob=vjobnew[:]

  if not method['geo']:
    if method['rpa']:
      regexp=re.compile('^#BEGIN EXECUTION SECTION')
      vjobnew=[]
      for line in vjob:
        if regexp.search(line):
          vjobnew.append(line)
          vjobnew.append('rirpa > rirpa.out'+'\n')
        else:
          vjobnew.append(line)
      vjob=vjobnew[:]
    if method['dft'] and scfparams['rij']:
      regexp=re.compile('^#BEGIN EXECUTION SECTION')
      vjobnew=[]
      for line in vjob:
        if regexp.search(line):
          vjobnew.append(line)
          vjobnew.append('ridft > ridft.out'+'\n')
        else:
          vjobnew.append(line)
      vjob=vjobnew[:]

  #then replace the entire file with the new vjob
  filinp=open(runjob,'w')
  for line in vjob:
    filinp.write(line)
  filinp.close()

######################################################################
# Main program
######################################################################

#----------------------------------------
# Basic method options
# The script is suited for DFT/RPA calculations.
# More advanced/broad usage must be still implemented.
#----------------------------------------
method={                   \
 'rpa':     True          , \
 'rpagrad': False          , \
 'dft':     True          , \
 'geo':     False          , \
 'dftfunc': 'pbe'         , \
 'basis':   'cc-pVQZ' , \
 'symm':    False         , \
 #only standard freezing at the moment
 'freeze':  True           \
}

#----------------------------------------
# Change less important options
#----------------------------------------
scfparams={                 \
 'scfconv':      '7'     ,  \
 'denconv':      '1.0d-7',  \
 'scftol' :      '1.0d-12', \
 'scfiterlimit': '300'   ,  \
 'dftgrid': '5'         ,  \
 # npoints  
 'rpagrid': '100'        ,  \
 'rij':     True         ,  \
 'dsp':     True         ,  \
 'maxcor':       '5000'     \
}

jobparams={                                                      \
 'jobtitle' : 'Dummy',                                        \
 'tmversion': '/modfac/apps/TURBOMOLE_v6.5', \
 'jobmem'   : str(int(scfparams['maxcor'])+1000),                \
 'jobdisc'  : '40'                 ,                             \
 'jobtime'  : 'mf_long'                                          \
}
#----------------------------------------
# Less important defaults
#----------------------------------------
# Input data file name for define
definp = 'define.inp'
# Coord data
defcoo = 'coord'
# Define output
defout = 'define.out'
# Runjob file
runjob = 'runjob'
# control file
filcon = 'control'
# Working directory
workdir = os.getcwd() 
# Create a series name to identify associate jobs in the queue
day,month,no,clock,year = time.ctime().split()
cno=clock.split(':')
series=''
for cs in cno:
  series=series+cs
print 'job series identifier',series
sys.stdout.flush()

#----------------------------------------
# Structure input. Number of atoms is
# obtained automatically from coord file
#----------------------------------------
os.chdir(workdir)
filtmp=open(defcoo,'r')
#note: this works only for a 'pure' coord file
natoms = len(filtmp.readlines())-2
body   = []
for iat in range(natoms):
  body.append(iat+1)
struct={          \
 'nbo'   :  1,    \
 'ndi'   :  0,    \
 'ntri'  :  0,    \
 'bodies':  [body],  \
  # Total charge of the system
 'charge':  0     \
}
#----------------------------------------

# In the special case of core weighted Dunning basis sets,
# it must be checked if H atoms are in the molecule
hfound=False
regexp = re.compile('pwCV')
if regexp.search(method['basis']):
  filtmp = open(defcoo,'r')
  lines = filtmp.readlines()
  filtmp.close()
  for iat in range(natoms):
    if lines[iat+1].split()[3]=='h':
      hfound=True
  
################
# Setup
################
os.chdir(workdir)

#Prepare text file for define setup
#no ghost atoms here
ghosts=[]
nshls=1
writedef(hfound,nshls,definp,method,struct,scfparams,ghosts) 

#coord and runjob must be in the workdir

#Run define (TURBOMOLE PATH must be setup)
os.system('define < '+definp+' > '+defout)

#Modify control
modcon(filcon,method,scfparams)

# Modify runjob
#jobparams['jobtitle'] = series
#modjob(runjob,jobparams,method,scfparams)

# Submit method
#os.system('qsub runjob')

print '***definp.py done***'
sys.stdout.flush()
