'''
Fit MC mass distributions
'''
from pprint import pprint
import ROOT
from brazil.aguapreta import *
ROOT.gROOT.SetBatch(True)

ROOT.gROOT.ProcessLine(open('models.cc').read())
from ROOT import MyErfc

figure_dir = "/home/dryu/BFrag/data/fits/mc"

MMIN=5.05
MMAX=5.5

# Fit bins
ptbins = [5.0, 10.0, 15.0, 20.0, 25.0, 30.0]
ybins = [0.0, 0.25, 0.50, 0.75, 1.00, 1.25, 1.50, 1.75, 2.0, 2.25]

fit_cuts = {}
fit_text = {} # Text for plots
fit_cuts["inclusive"] = "1"
fit_text["inclusive"] = "Inclusive"
for ipt in range(len(ptbins) - 1):
	cut_str = "(abs(y) < 2.25) && (pt > {}) && (pt < {})".format(ptbins[ipt], ptbins[ipt+1])
	cut_name = "ptbin_{}_{}".format(ptbins[ipt], ptbins[ipt+1]).replace(".", "p")
	fit_cuts[cut_name] = cut_str
	fit_text[cut_name] = "{}<pT<{}".format(ptbins[ipt], ptbins[ipt+1])

for iy in range(len(ybins) - 1):
	cut_str = "(pt > 5.0) && (pt < 30.0) && ({} < abs(y)) && (abs(y) < {})".format(ybins[iy], ybins[iy+1])
	cut_name = "ybin_{}_{}".format(ybins[iy], ybins[iy+1]).replace(".", "p")
	fit_cuts[cut_name] = cut_str
	fit_text[cut_name] = "{}<|y|<{}".format(ybins[iy], ybins[iy+1])

# Enums for PDFs
from enum import Enum
class BackgroundModel_t(Enum):
	kPolynomial = 1, 
	kChebychev = 2,
	kExp = 3

class SignalModel_t(Enum):
	kGaussian = 1,
	kDoubleGaussian = 2,
	kCB = 3

def pyerfc(x, par):
	erfc_arg = (x - par[0]) / par[1]
	return ROOT.TMath.Erfc(erfc_arg)

def plot_mc(tree, mass_range=[MMIN, MMAX], cut="", tag=""):
	h_mc = ROOT.TH1D("h_mc", "h_mc", 100, mass_range[0], mass_range[1])
	tree.Draw("mass >> h_mc", cut)
	c = ROOT.TCanvas("c_mc_{}".format(tag), "c_mc_{}".format(tag), 800, 600)
	h_mc.SetMarkerStyle(20)
	h_mc.GetXaxis().SetTitle("Fitted M_{J/#Psi K^{+}K^{-}} [GeV]")
	h_mc.Draw()
	c.SaveAs("/home/dryu/BFrag/data/fits/mc/{}.pdf".format(c.GetName()))


def fit_mc(tree, mass_range=[MMIN, MMAX], cut="1"):
	ws = ROOT.RooWorkspace('ws')

	cut = f"{cut} && (mass > {mass_range[0]}) && (mass < {mass_range[1]})"
	# Turn tree into RooDataSet
	mass = ws.factory(f"mass[{(mass_range[0]+mass_range[1])/2}, {mass_range[0]}, {mass_range[1]}]")
	pt = ws.factory(f"pt[10.0, 0.0, 200.0]")
	y = ws.factory("y[0.0, -5.0, 5.0]")
	rdataset = ROOT.RooDataSet("fitMC", "fitMC", ROOT.RooArgSet(mass, pt, y), ROOT.RooFit.Import(tree), ROOT.RooFit.Cut(cut))
	ndata = rdataset.sumEntries()

	# Signal: double Gaussian
	g1 = ws.factory(f"Gaussian::g1(mass, mean[{mass_range[0]}, {mass_range[1]}], sigma1[0.034, 0.001, 0.2])")
	g2 = ws.factory(f"Gaussian::g2(mass, mean, sigma2[0.15, 0.001, 0.2])")
	g3 = ws.factory(f"Gaussian::g3(mass, mean, sigma3[0.3, 0.001, 0.2])")
	c1 = ws.factory(f"c1[0.0, 1.0]")
	c2 = ws.factory(f"c2[0.0, 1.0]")
	#c3 = ws.factory(f"c3[0.0, 1.0]")
	signal_tg = ROOT.RooAddPdf("signal_tg", "signal_tg", ROOT.RooArgList(g1, g2, g3), ROOT.RooArgList(c1, c2), True)

	#signal_tg = ws.factory(f"SUM::signal_tg(f1[0.95, 0.01, 0.99]*g1, g2)")
	nsignal = ws.factory(f"nsignal[{ndata*0.5}, 0.0, {ndata*2.0}]")
	signal_model = ROOT.RooExtendPdf("signal_model", "signal_model", signal_tg, nsignal)

	model = ROOT.RooAddPdf("model", "model", ROOT.RooArgList(signal_model))

	# Perform fit
	##nll = model.createNLL(rdataset, ROOT.RooFit.NumCPU(8))
	#minimizer = ROOT.RooMinuit(nll)
	#minimizer.migrad()
	#minimizer.minos()
	fit_result = model.fitTo(rdataset, ROOT.RooFit.NumCPU(8), ROOT.RooFit.Save())

	# Generate return info
	#fit_result = minimizer.save()

	# Add everything to the workspace
	getattr(ws, "import")(rdataset)
	getattr(ws, "import")(model)
	return ws, fit_result

def plot_fit(ws, tag="", text=None):
	ROOT.gStyle.SetOptStat(0)
	ROOT.gStyle.SetOptTitle(0)

	model = ws.pdf("model")
	rdataset = ws.data("fitMC")
	xvar = ws.var("mass")

	canvas = ROOT.TCanvas("c_mcfit_{}".format(tag), "c_mcfit_{}".format(tag), 800, 800)

	top = ROOT.TPad("top", "top", 0., 0.5, 1., 1.)
	top.SetBottomMargin(0.02)
	top.Draw()
	top.cd()
	top.SetLogy()

	rplot = xvar.frame(ROOT.RooFit.Bins(100))
	rdataset.plotOn(rplot, ROOT.RooFit.Name("data"))
	model.plotOn(rplot, ROOT.RooFit.Name("fit"))
	model.plotOn(rplot, ROOT.RooFit.Name("signal"), ROOT.RooFit.Components("signal_model"), ROOT.RooFit.LineColor(ROOT.kGreen+2), ROOT.RooFit.FillColor(ROOT.kGreen+2), ROOT.RooFit.FillStyle(3002), ROOT.RooFit.DrawOption("LF"))
	rplot.GetXaxis().SetTitleSize(0)
	rplot.GetXaxis().SetLabelSize(0)
	rplot.GetYaxis().SetLabelSize(0.06)
	rplot.GetYaxis().SetTitleSize(0.06)
	rplot.GetYaxis().SetTitleOffset(0.8)
	rplot.Draw()

	l = ROOT.TLegend(0.7, 0.45, 0.88, 0.88)
	l.SetFillColor(0)
	l.SetBorderSize(0)
	l.AddEntry("data", "Data", "lp")
	l.AddEntry("fit", "Total fit", "l")
	l.AddEntry("signal", "B_{s}#rightarrowJ/#psi #phi", "lf")
	l.Draw()
	if text:
		textbox = ROOT.TLatex(0.15, 0.7, text)
		textbox.SetNDC()
		textbox.Draw()

	canvas.cd()
	bottom = ROOT.TPad("bottom", "bottom", 0., 0., 1., 0.5)
	bottom.SetTopMargin(0.02)
	bottom.SetBottomMargin(0.25)
	bottom.Draw()
	bottom.cd()

	binning = ROOT.RooBinning(100, MMIN, MMAX)
	data_hist = ROOT.RooAbsData.createHistogram(rdataset, "data_hist", xvar, ROOT.RooFit.Binning(binning))
	fit_binned = model.generateBinned(ROOT.RooArgSet(xvar), 0, True)
	fit_hist = fit_binned.createHistogram("model_hist", xvar, ROOT.RooFit.Binning(binning))
	pull_hist = data_hist.Clone()
	pull_hist.Reset()
	chi2 = 0.
	ndf = -7
	for xbin in range(1, pull_hist.GetNbinsX()+1):
		data_val = data_hist.GetBinContent(xbin)
		fit_val = fit_hist.GetBinContent(xbin)
		pull_val = (data_val - fit_val) / max(math.sqrt(fit_val), 1.e-10)
		pull_hist.SetBinContent(xbin, pull_val)
		pull_hist.SetBinError(xbin, 1)
		chi2 += pull_val**2
		ndf += 1
	pull_hist.GetXaxis().SetTitle("M_{J/#Psi K^{#pm}K^{#mp}} [GeV]")
	pull_hist.GetYaxis().SetTitle("Pull w.r.t. fit [#sigma]")
	pull_hist.SetMarkerStyle(20)
	pull_hist.SetMarkerSize(1)
	pull_hist.GetXaxis().SetTitleSize(0.06)
	pull_hist.GetXaxis().SetLabelSize(0.06)
	pull_hist.GetYaxis().SetTitleSize(0.06)
	pull_hist.GetYaxis().SetLabelSize(0.06)
	pull_hist.GetYaxis().SetTitleOffset(0.6)
	pull_hist.SetMinimum(-5.)
	pull_hist.SetMaximum(5.)
	pull_hist.Draw("p")

	zero = ROOT.TLine(MMIN, 0., MMAX, 0.)
	zero.SetLineColor(ROOT.kGray)
	zero.SetLineStyle(3)
	zero.SetLineWidth(2)
	zero.Draw()

	canvas.cd()
	top.cd()
	chi2text = ROOT.TLatex(0.15, 0.6, f"#chi^{{2}}/NDF={round(chi2/ndf, 2)}")
	chi2text.SetNDC()
	chi2text.Draw()

	canvas.cd()
	canvas.SaveAs("{}/{}.png".format(figure_dir, canvas.GetName()))
	canvas.SaveAs("{}/{}.pdf".format(figure_dir, canvas.GetName()))

	ROOT.SetOwnership(canvas, False)
	ROOT.SetOwnership(top, False)
	ROOT.SetOwnership(bottom, False)

def extract_yields(ws):
	return ws.var("nsignal").getVal()


if __name__ == "__main__":
	import argparse
	parser = argparse.ArgumentParser(description="Do Bu fits on data")
	parser.add_argument("--test", action="store_true", help="Do single test case (inclusive)")
	parser.add_argument("--all", action="store_true", help="Do all fit pT and y bins")
	parser.add_argument("--fits", action="store_true", help="Do fits")
	parser.add_argument("--plots", action="store_true", help="Plot fits")
	parser.add_argument("--tables", action="store_true", help="Make yield tables")
	args = parser.parse_args()

	import glob
	mc_files = glob.glob("MCEfficiency_Bu.root")

	if args.test: 
		cuts = ["inclusive"]
	elif args.all:
		cuts = sorted(fit_cuts.keys())

	if args.fits:
		for side in ["tag", "probe"]:
			if side == "probe":
				chain_name = "Bcands_probematch_Bu2KJpsi2KMuMu_probefilter".format(side)
			else:
				chain_name = "Bcands_tagmatch_Bu2KJpsi2KMuMu_inclusive".format(side)
			chain = ROOT.TChain(chain_name)
			#chain.Add("data_Run2018C_part3.root")
			#chain.Add("data_Run2018D_part1.root")
			#chain.Add("data_Run2018D_part2.root")
			for mc_file in mc_files:
				chain.Add(mc_file)

			for cut_name in cuts:
				cut_str = fit_cuts[cut_name]
				plot_mc(chain, cut=cut_str, tag="Bu_{}_{}".format(side, cut_name))

				ws, fit_result = fit_mc(chain, cut=cut_str)
				ws.Print()
				fit_result.Print()
				ws_file = ROOT.TFile("fitws_mc_Bu_{}_{}.root".format(side, cut_name), "RECREATE")
				ws.Write()
				fit_result.Write()
				ws_file.Close()

	if args.plots:
		for side in ["tag", "probe"]:
			for cut_name in cuts:
				ws_file = ROOT.TFile("fitws_mc_Bu_{}_{}.root".format(side, cut_name), "READ")
				#ws_file.ls()
				ws = ws_file.Get("ws")
				plot_fit(ws, tag="Bu_{}_{}".format(side, cut_name), text=fit_text[cut_name])

	if args.tables:
		yields = {}
		for side in ["tag", "probe"]:
			yields[side] = {}
			for cut_name in cuts:
				ws_file = ROOT.TFile("fitws_mc_Bu_{}_{}.root".format(side, cut_name), "READ")
				#ws_file.ls()
				ws = ws_file.Get("ws")
				yields[side][cut_name] = extract_yields(ws)
		pprint(yields)