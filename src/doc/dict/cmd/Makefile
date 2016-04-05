PDFLATEX=/usr/local/texlive/2015/bin/x86_64-darwin/pdflatex

LOWER_MISSION = $(shell echo $(BLISS_MISSION) | tr A-Z a-z)
CMDDICT       = ../../../config/$(LOWER_MISSION)/cmd.yaml

SOURCES = \
  cmddict.tex               \
  cmddict-01-defs.tex       \
  cmddict-02-preamble.tex   \
  cmddict-03-title.tex      \
  cmddict-04-signatures.tex \
  cmddict-05-changelog.tex  \
  cmddict-06-intro.tex      \
  cmddict-07-cmddefs.tex    \
  cmddict-08-acronyms.tex   \

YYYYMMDD=$(shell date "+%Y-%m-%d")
TEMPNAME=cmddict.pdf
FULLNAME=$(BLISS_MISSION)_CMD_Dictionary_$(YYYYMMDD).pdf

.PHONY: all copy

all: $(TEMPNAME) copy

copy: $(TEMPNAME)
	/bin/cp $(TEMPNAME) $(FULLNAME)

cmddict-07-cmddefs.tex: ./bliss-cmddefs-tex $(CMDDICT)
	./bliss-cmddefs-tex

$(TEMPNAME): $(SOURCES)
	$(PDFLATEX) $<
	$(PDFLATEX) $<

clean:
	/bin/rm -f *~ *.aux *.log *.out *.toc

distclean: clean
	/bin/rm -f *.pdf
