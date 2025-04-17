from src.config import CONFIG
from src.config import TaskConfig
from src.tasks._after_train import eval_on_datasets, eval_robustness
from src.trainer import Trainer
from src.utils.logger import get_default_logger
import torch.nn as nn
import pathlib
from omegaconf import OmegaConf

def assert_inputs(task_config: TaskConfig) -> None:
    assert task_config.task_params.fold is not None, 'Undefined training fold'
    assert task_config.cfg.experiment_name is not None, 'Undefined training experiment name'

def run(task_config: TaskConfig) -> None:
    assert_inputs(task_config)

    model_cfg = task_config.model
    params = task_config.task_params
    use_map = model_cfg.use_map

    run_cfg = OmegaConf.to_container(task_config.cfg, resolve=True)
    trainer = Trainer(
        filename=task_config.cfg.experiment_name,
        model=model_cfg.model,
        checkpoint_name=params.save_file,
        criterion=nn.PoissonNLLLoss(log_input=False),
        batch_size=model_cfg.batch_size,
        unmap_criterion=use_map,
        logger=get_default_logger(CONFIG.logs, run_cfg=run_cfg),
        task_config=task_config
    )

    train_chroms, val_chroms, test_chroms = CONFIG.get_chrom_split(task_config.task_params.fold)
    #train_chroms, val_chroms = [22], [13]

    train_dataset = params.train_dataset
    val_dataset = params.val_dataset
    train_dataset.set_chroms(train_chroms)
    val_dataset.set_chroms(val_chroms)

    trainer.fit(
        train_dset=train_dataset,
        val_dset=val_dataset,
        nr_epochs=params.trainer.max_epochs,
        learning_rate=model_cfg.learning_rate
    )

    # for evaluation use the checkpoint of the best model
    print(f'Loading best model weights from {trainer.filename}')
    checkpoint_path = pathlib.Path(trainer.logger.logs_dir) / trainer.filename / 'checkpoint.pth'
    trainer.load_weights(checkpoint_path)

    experiment_spec = dict(
        checkpoint=trainer.filename,
        model=task_config.model.name,
        experiment=task_config.cfg.experiment_name,
        cell_line=task_config.cell_line.exp_name
    )

