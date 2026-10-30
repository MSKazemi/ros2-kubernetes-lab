# Shortcuts for the `lab` command line. This file holds no logic: every target just runs
# ./lab, so `make` and `./lab` can never disagree. See `./lab --help` and docs/CLI.md.
#
# Linux and macOS (the GNU make 3.81 that macOS ships is enough). On Windows use lab.cmd, or
# run make from WSL or Git Bash.
#
#   make                                  list the targets
#   make check                            run the repository checks
#   make cluster-up LABFLAGS=--dry-run    preview a command without running it
LAB ?= ./lab
LABFLAGS ?=
NODE ?=

.DEFAULT_GOAL := help
.PHONY: help doctor check check-shell check-links check-site image-build image-test image-shell \
	cluster-status cluster-up cluster-ssh cluster-halt cluster-destroy lab

help: ## Show this list
	@echo "ROS 2 on Kubernetes lab - make shortcuts (each target runs ./lab)"
	@echo
	@grep -hE '^[a-zA-Z0-9_-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "} {printf "  make %-16s %s\n", $$1, $$2}'
	@echo
	@echo "Examples:"
	@echo "  make doctor                          can this machine run the lab?"
	@echo "  make image-build image-test          build and smoke-test the Jazzy image"
	@echo "  make cluster-up LABFLAGS=--dry-run   show the command, start nothing"
	@echo "  make lab ARGS='cluster ssh worker1'  run any lab command"
	@echo
	@echo "Full command line: ./lab --help   |   Tab completion: ./lab completion --help"

doctor: ## Check this machine (read-only)
	@$(LAB) doctor $(LABFLAGS)

check: ## Run every repository check
	@$(LAB) check $(LABFLAGS)

check-shell: ## Bash syntax of the provisioning scripts
	@$(LAB) check shell $(LABFLAGS)

check-links: ## Local Markdown links and anchors
	@$(LAB) check links $(LABFLAGS)

check-site: ## Static website files
	@$(LAB) check site $(LABFLAGS)

image-build: ## Build the ROS 2 Jazzy image
	@$(LAB) image build $(LABFLAGS)

image-test: ## Smoke-test the image (one container only)
	@$(LAB) image test $(LABFLAGS)

image-shell: ## Open a shell in the image
	@$(LAB) image shell $(LABFLAGS)

cluster-status: ## Show the historical Vagrant VMs
	@$(LAB) cluster status $(LABFLAGS)

cluster-up: ## Start the historical 3-VM cluster (asks first)
	@$(LAB) cluster up $(LABFLAGS)

cluster-ssh: ## Log in to a node: make cluster-ssh NODE=worker1
	@$(LAB) cluster ssh $(NODE) $(LABFLAGS)

cluster-halt: ## Stop the VMs, keep their disks
	@$(LAB) cluster halt $(LABFLAGS)

cluster-destroy: ## Delete the VMs (asks first)
	@$(LAB) cluster destroy $(LABFLAGS)

lab: ## Run any lab command: make lab ARGS="cluster ssh worker1"
	@$(LAB) $(ARGS) $(LABFLAGS)
