#PDFLATEX=/usr/local/texlive/2015/bin/x86_64-darwin/pdflatex

LOWER_MISSION = $(shell echo $(BLISS_MISSION) | tr A-Z a-z)
CMDDICT       = /Users/jpadams/Documents/proj/oco3/workspace/oco3-devmode/oco3mos/config/tlm/fsw3/tlm.yaml

SOURCES = \
  tlmdict.tex               \
  tlmdict-01-defs.tex       \
  tlmdict-02-preamble.tex   \
  tlmdict-03-title.tex      \
  tlmdict-04-signatures.tex \
  tlmdict-05-changelog.tex  \
  tlmdict-06-intro.tex      \
  tlmdict-07-tlmdefs.tex    \
  tlmdict-08-acronyms.tex   \

YYYYMMDD=$(shell date "+%Y-%m-%d")
TEMPNAME=tlmdict.pdf
FULLNAME=$(BLISS_MISSION)_TLM_Dictionary_$(YYYYMMDD).pdf

.PHONY: all copy

all: $(TEMPNAME) copy

copy: $(TEMPNAME)
	/bin/cp $(TEMPNAME) $(FULLNAME)

tlmdict-07-tlmdefs.tex: ./bliss-tlmdefs-tex $(TLMDICT)
	./bliss-tlmdefs-tex

$(TEMPNAME): $(SOURCES)
	pdflatex $<
	pdflatex $<

clean:
	/bin/rm -f *~ *.aux *.log *.out *.toc

distclean: clean
	/bin/rm -f *.pdf
