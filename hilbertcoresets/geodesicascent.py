import numpy as np
import captree as ct

class GIGA(object):
  def __init__(self, x):
    self.norms = np.sqrt((x**2).sum(axis=1))
    self.sig = self.norms.sum()
    if np.any(self.norms==0):
      print 'Error: No vectors in x can have 0 norm'
    self.x = x
    self.xs = x.sum(axis=0)
    self.y = x/self.norms[:, np.newaxis]
    self.ys = self.xs/np.sqrt(((self.xs)**2).sum())
    self.N = x.shape[0]
    self.tree = None
    self.f_tree = 0.
    self.m_tree = 0.
    self.s_tree = 0.
    self.n_tree = 0.
    self.f_lin = 0.
    #self.m_lin = 0.
    #self.s_lin = 0.
    self.n_lin = 0.
    self.reset()

  #update_method can be 'fast' or 'stable'
  #search_method can be 'adaptive', 'linear', or 'tree'
  def run(self, M, update_method='fast', search_method='adaptive', M_max = None):
    if M <= self.M:
      print 'Warning: requested M <= self.M, returning without modifying weights'
      return

    if search_method == 'linear':
      GIGA.search = GIGA.search_linear
    elif search_method == 'tree':
      GIGA.search = GIGA.search_tree
      if not self.tree:
        self.build_tree()
    else:
      if not M_max:
        M_max = M
      if self.tree:
        GIGA.search = GIGA.search_adaptive
      elif not self.tree and Mmax - self.M >= (4*self.N+3)*np.log2(self.N)/(2.*(self.N+1-np.log2(self.N))):
        GIGA.search = GIGA.search_adaptive
        self.build_tree()
      else:
        GIGA.search = GIGA.search_linear

    #this is commented out since initialization step is exactly the same as the main iteration if y(w) = 0
    #this is true for both tree and linear search
    #if self.M == 0:
    #  scores = self.y.dot(self.ys)
    #  f = scores.argmax()
    #  self.wts[f] = 1.
    #  self.yw = self.y[f, :]
    #  self.M = 1

    for m in range(self.M, M):
      f = self.search()

      gA = self.ys.dot(self.yw)
      gB = self.ys.dot(self.y[f,:])
      gC = self.yw.dot(self.y[f,:])
      gamma = (gB-gA*gC) / ((gB-gA*gC) + (gA-gB*gC))

      if gamma < 0 or gamma > 1:
        print 'Warning: gamma not in [0, 1]: ' + str(gamma)
        gamma = (0. if gamma < 0 else gamma)
        gamma = (1. if gamma > 1 else gamma)

      self.wts *= (1.-gamma)
      self.wts[f] += gamma

      if update_method == 'fast':
        self.yw = (1.-gamma)*self.yw + gamma*self.y[f, :]
      else:
        self.yw = (self.wts[:, np.newaxis]*self.y).sum(axis=0)

      nrm = np.sqrt((self.yw**2).sum())
      self.yw /= nrm
      self.wts /= nrm

    self.M = M
    return

  def search_linear(self):
    cdir = self.ys - self.ys.dot(self.yw)*self.yw
    scorenums = self.y.dot(cdir) 
    scoredenoms = 1.-self.y.dot(self.yw)**2
    scoredenoms[scoredenoms < 1e-16] = np.inf
    scores = scorenums/np.sqrt(scoredenoms)
    #cdir /= np.sqrt((cdir**2).sum())
    #dirs = self.y - self.y.dot(self.yw)[:,np.newaxis]*self.yw
    #dirnrms = np.sqrt((dirs**2).sum(axis=1))
    #dirnrms[dirnrms < 1e-16] = np.inf #this is only really used in iteration M=2, where yw = the initial vector
    #dirs /= dirnrms[:, np.newaxis]
    #scores = dirs.dot(cdir)
    self.f_lin += 2.*N+2.
    #self.s_lin += np.log(2.*N+2.)**2
    #self.m_lin += np.log(2.*N+2.)
    self.n_lin += 1
    return scores.argmax()
  
  def search_tree(self):
    cdir = self.ys - self.ys.dot(self.yw)*self.yw
    cdir /= np.sqrt((cdir**2).sum())
    nopt, nfun = ct.cap_tree_search(self.tree, self.yw, cdir)
    self.f_tree += nfun
    self.m_tree += np.log(nfun)
    self.s_tree += np.log(nfun)**2
    self.n_tree += 1
    return nopt
  
  def search_adaptive(self):
    #this uses UCB1-Normal from Auer et al ``Finite-time Analysis of the Multiarmed Bandit Problem'' (2002)
    #modification: since we know linear search is 2N+2 ops, dont need confidence bounds for that
    n = self.n_tree+self.n_lin + 1
    #if self.n_lin < 2 or self.n_lin < np.ceil(8.*np.log(n)):
    #  return self.search_linear()
    if self.n_tree < 2 or self.n_tree < np.ceil(8.*np.log(n)):
      return self.search_tree()
    #lin_idx = self.m_lin/self.n_lin + np.sqrt(16.*((self.s_lin - self.m_lin**2/self.n_lin)/(self.n_lin-1))*(np.log(n-1.)/self.n_lin))
    tree_idx = self.m_tree/self.n_tree - np.sqrt(16.*((self.s_tree - self.m_tree**2/self.n_tree)/(self.n_tree-1))*(np.log(n-1.)/self.n_tree))
    if tree_idx < np.log(2.*N+2):
      return self.search_tree()
    else:
      return self.search_linear()

  def build_tree(self):
    self.tree = ct.CapNode(self.y)

  def reset(self):
    self.M = 0
    self.wts = np.zeros(self.N)
    self.yw = np.zeros(self.y.shape[1])

  def error(self):
    return np.sqrt((self.xs**2).sum())*np.sqrt(((self.yw-self.ys)**2).sum())

  def weights(self):
    return (self.wts/self.norms)*np.sqrt((self.xs**2).sum())*self.yw.dot(self.ys)

  #def exp_bound(self, M=None):
  #  if not self._diam:
  #    self._compute_diam()
  #  if not self._nu:
  #    self._compute_nu()
  #  normratio = np.sqrt(1. - (self.xs**2).sum()/self.sig**2)
  #  return self.sig*self._diam/np.sqrt(M if M else self.M)
  #
  #def sqrt_bound(self, M=None):
  #  if not self._diam:
  #    self._compute_diam()
  #  return self.sig*self._diam/np.sqrt(M if M else self.M)

  #def _compute_nu(self):
  #  #from scipy.spatial import ConvexHull
  #  #from xx import linear programming
  #  #hull = ConvexHull(self.x)
  #  #hull.equations[:, :-1]
  #  #hull.equations[:, -1]
  #  #self.xs
  #  self._nu = 1.
  #  return

  #def _compute_diam(self):
  #  normed_x = self.x/self.norms[:, np.newaxis] 
  #  distsqs = 2. - 2.*normed_x.dot(normed_x.T)
  #  self._diam = np.sqrt(distsqs.max())
  #  return
