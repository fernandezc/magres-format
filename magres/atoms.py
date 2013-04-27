import os
import math
import constants
import numpy
from peak.util.proxies import ObjectWrapper
from format import MagresFile

class MagresAtomEfg(object):
  def __init__(self, atom, magres_efg):
    self.atom = atom
    self.magres_efg = magres_efg

  @property
  def V(self):
    return numpy.array(self.magres_efg['V'])

  @property
  def Cq(self):
    try:
      return constants.efg_to_Cq_isotope(self.V, self.atom.species, self.atom.isotope)
    except KeyError:
      return 0.0

class MagresAtomIsc(object):
  def __init__(self, atom1, atom2, magres_isc):
    self.atom1 = atom1
    self.atom2 = atom2
    self.magres_isc = magres_isc

  @property
  def symbol(self):
    return "%s -> %s" % (self.atom1, self.atom2)

  @property
  def dist(self):
    return self.atom1.dist(self.atom2.position)

  @property
  def K(self):
    return numpy.array(self.magres_isc['K'])
  
  @property
  def K_iso(self):
    return numpy.trace(self.K)/3.0

  @property
  def J(self):
    return constants.K_to_J_iso(self.K, self.atom1.species, self.atom1.isotope, self.atom2.species, self.atom2.isotope)

  @property
  def J_iso(self):
    return numpy.trace(self.J)/3.0

  @property
  def K_sym(self):
    return (self.K + self.K.T)/2.0
  
  @property
  def K_asym(self):
    return (self.K - self.K.T)/2.0
  
  @property
  def J_sym(self):
    return (self.J + self.J.T)/2.0
  
  @property
  def J_asym(self):
    return (self.J - self.J.T)/2.0

  def haeberlen_pcs(self, tensor):
    evals, evecs = numpy.linalg.eig(tensor)
    iso = sum(evals)/3.0
    evals = sorted(evals, key=lambda x: abs(x - iso))

    return (evals[1], evals[0], evals[2])

  @property
  def K_haeberlen(self):
    return self.haeberlen_pcs(self.K)
  
  @property
  def J_haeberlen(self):
    return self.haeberlen_pcs(self.J)

  @property
  def K_aniso(self):
    jx = self.K_haeberlen
    return jx[2] - (jx[0] + jx[1])/2.0
  
  @property
  def J_aniso(self):
    jx = self.J_haeberlen
    return jx[2] - (jx[0] + jx[1])/2.0

  @property
  def K_eta(self):
    jx = self.K_haeberlen
    return (jx[1] - jx[0]) / (jx[2] - sum(jx)/3.0)
  
  @property
  def J_eta(self):
    jx = self.J_haeberlen
    return (jx[1] - jx[0]) / (jx[2] - sum(jx)/3.0)

class MagresAtomMs(object):
  def __init__(self, atom, magres_ms, reference=None):
    self.atom = atom
    self.magres_ms = magres_ms
    self.reference = reference

  @property
  def sigma(self):
    return self.magres_ms['sigma']

  @property
  def iso(self):
    if self.reference is None:
      reference = 0.0
    else:
      reference = self.reference

    return reference - numpy.trace(self.sigma)/3.0

class MagresAtom(object):
  def __init__(self, magres_atom):
    self.magres_atom = magres_atom

  def __str__(self):
    if self.species != self.label:
      return "%d%s(%s)%d" % (self.isotope, self.species, self.label, self.index)
    else:
      return "%d%s%d" % (self.isotope, self.species, self.index)

  def dist(self, r):
    if type(r) in [MagresAtom, MagresAtomImage]:
      r = r.position
    dr = self.position - r
    return math.sqrt(numpy.dot(dr, dr))

  @property
  def label(self):
    return self.magres_atom['label']
  
  @property
  def species(self):
    return self.magres_atom['species']
  
  @property
  def index(self):
    return self.magres_atom['index']
  
  @property
  def position(self):
    return numpy.array(self.magres_atom['position'])

  @property
  def isotope(self):
    if hasattr(self, '_isotope'):
      return self._isotope
    else:
      if self.species in constants.gamma_iso:
        return constants.gamma_iso[self.species]
      else:
        return None

  @isotope.setter
  def isotope(self, value):
    if (self.species, value) in constants.gamma:
      self._isotope = value
    else:
      raise ValueError("Unknown NMR isotope %d%s" % (value, self.species))

  @property
  def gamma(self):
    if self.isotope in constants.gamma:
      return constants.gamma[self.isotope]
    else:
      return 0.0
  
  @property
  def Q(self):
    if self.isotope in constants.Q:
      return constants.Q[self.isotope]
    else:
      return 0.0

class MagresAtomImage(ObjectWrapper):
  """
    Proxy object view into a MagresAtom for periodic images.
    Read-only position, otherwise identical.
  """

  def __init__(self, atom, position):
    super(MagresAtomImage, self).__init__(atom)
    self._position = position

  @property
  def position(self):
    return self._position

  def dist(self, r):
    if type(r) in [MagresAtom, MagresAtomImage]:
      r = r.position
    dr = self.position - r
    return math.sqrt(numpy.dot(dr, dr))

class MagresAtoms(object):
  def __init__(self, atoms=None):
    if atoms is not None:
      if type(atoms) == list:
        self.atoms = atoms
      elif type(atoms) == MagresFile:
        self.from_magres(atoms) 
    else:
      self.atoms = []

    self.label_index = {}
    self.species_index = {}

    self.build_index()

  def from_magres(self, magres_file):
    self.magres_file = magres_file
    atoms = []

    if 'lattice' in magres_file.data_dict['atoms'] and len(magres_file.data_dict['atoms']['lattice']) == 1:
      self.lattice = numpy.array(magres_file.data_dict['atoms']['lattice'][0])

    temp_label_index = {}
    for magres_atom in magres_file.data_dict['atoms']['atom']:
      atom = MagresAtom(magres_atom)

      temp_label_index[(atom.label, atom.index)] = atom

      atoms.append(atom)

    ms_types = ['ms']
    for ms_type in ms_types:
      if ms_type not in magres_file.data_dict['magres']:
        continue
      
      setattr(self, ms_type, [])

      for magres_ms in magres_file.data_dict['magres'][ms_type]:
        atom = temp_label_index[(magres_ms['atom']['label'], magres_ms['atom']['index'])]
        magres_atom_ms = MagresAtomMs(atom, magres_ms)
        getattr(self, ms_type).append(magres_atom_ms)
        setattr(atom, ms_type, magres_atom_ms)

    efg_types = ['efg', 'efg_local', 'efg_nonlocal']
    for efg_type in efg_types:
      if efg_type not in magres_file.data_dict['magres']:
        continue
      
      setattr(self, efg_type, [])

      for magres_efg in magres_file.data_dict['magres'][efg_type]:
        atom = temp_label_index[(magres_efg['atom']['label'], magres_efg['atom']['index'])]
        magres_atom_efg = MagresAtomEfg(atom, magres_efg)
        getattr(self, efg_type).append(magres_atom_efg)
        setattr(atom, efg_type, magres_atom_efg)
    
    isc_types = ['isc', 'isc_spin', 'isc_fc', 'isc_orbital_p', 'isc_orbital_d']
    for isc_type in isc_types:
      if isc_type not in magres_file.data_dict['magres']:
        continue

      setattr(self, isc_type, [])

      for magres_isc in magres_file.data_dict['magres'][isc_type]:
        atom1 = temp_label_index[(magres_isc['atom1']['label'], magres_isc['atom1']['index'])]
        atom2 = temp_label_index[(magres_isc['atom2']['label'], magres_isc['atom2']['index'])]
        magres_atom_isc = MagresAtomIsc(atom1, atom2, magres_isc)
        getattr(self, isc_type).append(magres_atom_isc) 

    self.atoms = atoms

  @classmethod
  def load_magres(self, f):
    if type(f) == str and os.path.isfile(f):
      magres_file = MagresFile(open(f))
    else:
      magres_file = MagresFile(f)

    return MagresAtoms(magres_file)

  def add(self, atoms):
    if type(atoms) == Atom:
      self.atoms.append(atoms)
    elif type(atom) == list:
      for atom in atoms:
        self.atoms.append(atom)

    self.build_index()

  def build_index(self):
    self.label_index.clear()
    self.species_index.clear()

    for atom in self.atoms:
      if atom.label in self.label_index:
        self.label_index[atom.label].append(atom)
      else:
        self.label_index[atom.label] = [atom]
      
      if atom.species in self.species_index:
        self.species_index[atom.species].append(atom)
      else:
        self.species_index[atom.species] = [atom]

  def get_label(self, label, index=None):
    if index is None:
      return self.label_index[label]
    else:
      return self.label_index[label][index-1]

  def get_species(self, label, index=None):
    if index is None:
      return self.species_index[label]
    else:
      return self.species_index[label][index-1]

  def within(self, pos, max_dr):
    if type(pos) is MagresAtom:
      pos = pos.position

    atoms = []
    for atom in self.atoms:
      dr, min_p = self.least_mirror(atom.position, pos)

      if dr <= max_dr:
        atoms.append(MagresAtomImage(atom, min_p))

    return atoms

  def least_mirror(self, a, b):
    """
      Give the closest periodic image of a to b given the current lattice.
    """
    min = None
    min_p = None

    for i in range(-1,2):
      for j in range(-1,2):
        for k in range(-1,2):
          ap = numpy.add(a, numpy.dot(self.lattice.T, (float(i), float(j), float(k))))
          r = numpy.subtract(ap, b)
          d = numpy.dot(r, r)

          if min is None or d < min:
            min = d
            min_p = ap

    return (math.sqrt(min), min_p)

  def __getitem__(self, idx):
    if type(idx) == tuple:
      s, i = idx
      return self.get_species(s, i)
    else:
      return self.atoms[idx]

  def __iter__(self):
    return self.atoms.__iter__()
