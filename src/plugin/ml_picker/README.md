# ML Auto-Picker Plugin

LSTM-based automatic first-break picker for seismic traces.

## Requirements

- PyTorch (`pip install torch`)

## Model Weights

Place your trained model weights (`.pt` files) in the `models/` directory:

- `models/best_model_bilstm.pt` — Bidirectional LSTM model
- `models/best_model_unidirectional.pt` — Unidirectional LSTM model

## Usage

When this plugin is present and PyTorch is installed, an **ML** menu will appear
in the TraceMax menu bar with the **BiLSTM Auto-Picker** option.

If PyTorch is not installed, the core application works normally — the ML menu
simply won't appear.
