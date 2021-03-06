import argparse
import copy
from matplotlib import pyplot as plt
import os
import pickle
import sys
from tqdm import tqdm

import torch
from torch import optim
from torch.utils import data

sys.path.append(os.getcwd())
from data import snli_ve_dataset as snli
from helper import plotter
from models import snli_models as models


def parse_args():
    parser = argparse.ArgumentParser(description='Fine-tune classifier for SNLI-VE task using precomputed embeddings.')
    parser.add_argument(
        '--plot',
        default=False,
        action='store_true',
        help='Use it if you want to create plots of loss values during fine-tuning.'
    )
    parser.add_argument(
        '--eval',
        default=False,
        action='store_true',
        help='Use it if you want to evaluate the fine-tuned model on SNLI-VE.'
    )

    parser.add_argument(
        '--epochs',
        type=int,
        default=300,
        help='Number of epochs for the fine-tuning process.'
    )
    parser.add_argument(
        "--lr",
        type=float,
        default=0.0001,
        help='Initial learning rate of the fine-tuning process.'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=128,
        help='Number of image and sentence pairs per batch.'
    )
    parser.add_argument(
        '--input-size',
        type=int,
        default=1024,
        help="Input embedding's size."
    )
    parser.add_argument(
        '--hidden-size',
        type=int,
        default=100,
        help="Regressor's hidden size (h_s)."
    )
    parser.add_argument(
        '--momentum',
        type=float,
        default=0.0,
        help='Momentum of SGD optimizer.'
    )
    parser.add_argument(
        '--weight-decay',
        type=float,
        default=0.0,
        help='Weight decay of SGD optimizer.'
    )
    parser.add_argument(
        '--dropout',
        type=float,
        default=0.0,
        help='Dropout probability.'
    )
    parser.add_argument(
        '--batch-norm',
        default=False,
        action='store_true',
        help='Use batch normalization layers in classifier.'
    )

    parser.add_argument(
        "--emb-file",
        type=str,
        help='Numpy file with concatenated embeddings of image and hypothesis of each instance.'
    )
    parser.add_argument(
        "--label-file",
        type=str,
        help='Numpy file with labels of SNLI_VE dataset.'
    )
    parser.add_argument(
        "--output-path",
        type=str,
        help='Path for output files.'
    )

    return parser.parse_args()


# TODO: CHANGE THIS FUNCTION TO ADAPT IT TO SNLI-VE
def inference(data_gen, model, device):

    all_logits = []

    for batch in data_gen:

        emb_1, emb_2, _ = batch
        logits = model(emb_1.to(device), emb_2.to(device))
        _, pred_labels = torch.max(logits, 1)
        all_logits.extend(pred_labels.squeeze(1).data.cpu().tolist())

    return all_logits


def main():

    args = parse_args()

    print("A) Load data")
    train_data = snli.SnliVECaptionsPrecomp(
        file_emb=args.emb_file, file_label=args.sim_file, split="train"
    )
    dev_data = snli.SnliVECaptionsPrecomp(
        file_emb=args.emb_file, file_label=args.sim_file, split="dev"
    )

    print("B) Load model")
    device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')

    model = models.SnliClassifier(
        input_dim=args.input_size, hidden_dim=args.hidden_size, dropout=args.dropout, batch_norm=args.batch_norm
    )
    model = model.to(device)

    # Observe that all parameters are being optimized
    optimizer = optim.SGD(model.parameters(), lr=args.lr, weight_decay=args.weight_decay, momentum=args.momentum)

    print("C) Train model")
    train_params = {
        'batch_size': args.batch_size,
        'shuffle': True,
        'num_workers': 6
    }
    train_gen = data.DataLoader(train_data, **train_params)

    eval_params = {
        'batch_size': args.batch_size,
        'shuffle': False,
        'num_workers': 6
    }
    dev_gen = data.DataLoader(dev_data, **eval_params)

    train_losses = []
    dev_losses = []

    best_model_wts = copy.deepcopy(model.state_dict())
    best_loss = 1e10

    t_epoch = tqdm(range(1, args.epochs + 1), desc="Epoch")
    for _ in t_epoch:

        # Each epoch has a training and development phase
        for phase in ['train', 'dev']:
            if phase == 'train':
                generator = train_gen
                model.train()  # Set model to training mode
            else:
                generator = dev_gen
                model.eval()  # Set model to evaluate mode

            running_loss = 0.0
            idx = 0

            # Iterate over data.
            for current_batch in generator:

                emb, label = current_batch
                logits = model(emb.to(device))

                label = label.view(-1, 1).to(device)
                loss = model.criterion(logits, label)

                if phase == "train":
                    optimizer.zero_grad()
                    loss.backward()
                    optimizer.step()

                batch_loss = float(loss.data.cpu().numpy())
                running_loss += batch_loss
                idx += 1

            running_loss /= idx

            if phase == "train":
                train_losses.append(running_loss)
            else:
                dev_losses.append(running_loss)
                t_epoch.set_description(f"Epoch Loss: {train_losses[-1]:.3f} (train) / {dev_losses[-1]:.3f} (val)")

                # Deep copy the model if it's the best rsum
                if running_loss < best_loss:
                    del best_model_wts
                    best_loss = running_loss
                    best_model_wts = copy.deepcopy(model.state_dict())

    model.load_state_dict(best_model_wts)
    torch.save(model.state_dict(), os.path.join(args.output_path, f"ft_model_lr{args.lr:.1E}.pth"))

    # Save loss plot
    if args.plot:
        fig = plotter.plot_loss_curve(range(1, args.epochs + 1), train_losses, dev_losses, yexp=True)
        plt.savefig(os.path.join(args.output_path, f"training_losses_{args.lr:.1E}.png"))
        plt.close(fig)

    with open(os.path.join(args.output_path, "losses.pickle"), "wb") as f:
        losses = {"train": train_losses, "dev": dev_losses}
        pickle.dump(losses, f)

    if args.eval:

        test_data = snli.SnliVECaptionsPrecomp(
            file_emb=args.emb_file, file_label=args.sim_file, split="test"
        )
        train_gen = data.DataLoader(train_data, **eval_params)
        test_gen = data.DataLoader(test_data, **eval_params)

        print("D) Inference")
        model.eval()
        pred_train = inference(train_gen, model, device)
        pred_dev = inference(dev_gen, model, device)
        pred_test = inference(test_gen, model, device)

        print("E) Compute Accuracy (between predicted labels and ground truth)")
        pearson_values = [
            sum(1 for x, y in zip(pred_train, train_data.label) if x == y) / len(pred_train),
            sum(1 for x, y in zip(pred_dev, dev_data.label) if x == y) / len(pred_dev),
            sum(1 for x, y in zip(pred_test, test_data.label) if x == y) / len(pred_test)
        ]

        print(f"\t\t\tTRAIN\tDEV\tTEST")
        print(f"Accuracies: {pearson_values[0]:.4f}\t{pearson_values[1]:.4f}\t{pearson_values[2]:.4f}")


if __name__ == '__main__':
    main()
