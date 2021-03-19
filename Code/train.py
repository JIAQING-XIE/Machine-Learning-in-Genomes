import os
import torch
from torch import nn, optim
from torch.autograd import Variable
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
from sklearn.metrics import r2_score, mean_squared_error
import pandas as pd
from sklearn.preprocessing import Normalizer

from mlp_batchnorm import MLP_batchnorm
from mlp_simple import MLP_simple

from lantentDataset import LatentDataset

learning_rate = 0.001


dataFile = os.path.join('.\\data', 'LatentVec_Drug+GeneExp(cgc+sampledGene+unsampledDrug).txt')



num=0
while num<15:
    num += 1
    print("-----------------------------\n-------------"+str(num)+"---------------\n-----------------------------")

    data = pd.read_csv(open(dataFile), sep='\t')


    data = data.sample(frac=1).reset_index(drop=True)

    trainData = data.loc[: 2999, :]
    trainDataset = LatentDataset(trainData, train0val1test2=0)
    validationData = data.loc[3000: 3164, :]
    validationDataset = LatentDataset(validationData, train0val1test2=1)
    testData = data.loc[3165: 3329, :]
    testDataset = LatentDataset(testData, train0val1test2=2)

    trainLoader = DataLoader(trainDataset, batch_size=64, shuffle=True, drop_last=True)
    validationLoader = DataLoader(validationDataset, batch_size=165, drop_last=True)
    testLoader = DataLoader(testDataset, batch_size=165, drop_last=True)


    model = MLP_simple()
    '''
    for m in model.modules():
        if isinstance(m, (nn.Conv2d, nn.Linear)):
            nn.init.kaiming_normal_(m.weight, mode='fan_in')
    '''

    if torch.cuda.is_available():
        model = model.cuda()

    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate, weight_decay=0.0005)


    epoch = 0
    bestR2 = -1
    bestLoss = 200
    bestEpoch = 0
    path = '.\\trainedModels\\'
    while epoch < 5:

        model.train()
        for batch in trainLoader:

            geLatentVec, dLatentVec, target = batch

            # if geLatentVec.shape[0] != 50:
            #     continue

            if torch.cuda.is_available():
                geLatentVec = geLatentVec.cuda()
                dLatentVec = dLatentVec.cuda()
                target = target.cuda()
            else:
                geLatentVec = Variable(geLatentVec)
                dLatentVec = Variable(dLatentVec)
                target = Variable(target)
            out = model(geLatentVec, dLatentVec)
            loss = criterion(out, target)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        epoch += 1
        if epoch % 2 == 0:

            model.eval()

            for batch in validationLoader:
                geLatentVec, dLatentVec, target = batch
                if torch.cuda.is_available():
                    geLatentVec = geLatentVec.cuda()
                    dLatentVec = dLatentVec.cuda()
                    target = target.cuda()

                out = model(geLatentVec, dLatentVec)

                out = out.data.cpu().numpy().tolist()
                target = target.cpu().numpy().tolist()
                r2 = r2_score(target, out)
                rmse = mean_squared_error(target, out)**0.5
                # SS_tot = torch.std(target)
                # SS_res = evalLoss

                print('epoch: {}, Validation Loss: {:.6f}, R2_Score: {:.6f}'.format(epoch, rmse, r2))
                if (r2 > bestR2 and epoch>20):
                    bestLoss = rmse
                    bestR2 = r2
                    bestEpoch = epoch
                    torch.save(model.state_dict(), path + 'modelParameters.pt')
                    print("Got a better model!")
            # print('epoch: {}, loss: {:.4}'.format(epoch, loss.data.item()))
        pass


    path = '.\\trainedModels\\'
    model.load_state_dict(torch.load(path + 'modelParameters.pt'))
    print('\nNow testing the best model on test dataset\n')
    model.eval()
    for batch in testLoader:
        geLatentVec, dLatentVec, target = batch
        if torch.cuda.is_available():
            geLatentVec = geLatentVec.cuda()
            dLatentVec = dLatentVec.cuda()
            target = target.cuda()

        out = model(geLatentVec, dLatentVec)

        out = out.data.cpu().numpy().tolist()
        target = target.cpu().numpy().tolist()
        r2 = r2_score(target, out)
        rmse = mean_squared_error(target, out) ** 0.5

        print('epoch: {}, Validation Loss: {:.6f}, R2_Score: {:.6f}'.format(bestEpoch, bestLoss, bestR2))
        print('Test Loss: {:.6f}, R2_Score: {:.6f}'.format(rmse, r2))

        with torch.no_grad():
        plt.scatter(target, out)
        plt.xlabel("true drug response")
        plt.ylabel("predicted drug response")
        plt.title('Test Loss: {:.6f}, R2_Score: {:.6f}'.format(evalLoss, r2))
        
        
        df = pd.read_csv('.\\R2_Score(cgc+sampledGene+unsampledDrug).txt', sep='\t')
        df = df.append({'id': int(len(df)),
                        'R2_test': r2,
                        'RMSE_test': rmse,
                        'R2_val': bestR2,
                        'RMSE_val': bestLoss,
                        'epoch': bestEpoch},
                        ignore_index=True)
        df.to_csv('.\\R2_Score(cgc+sampledGene+unsampledDrug).txt', sep='\t', index=False)








