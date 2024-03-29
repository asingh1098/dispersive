from ImportFile import *

pi = math.pi


class Swish(nn.Module):
    def __init__(self, ):
        super().__init__()

    def forward(self, x):
        # pre-activation
        return x * torch.sigmoid(x)


def activation(name):
    if name in ['tanh', 'Tanh']:
        return nn.Tanh()
    elif name in ['relu', 'ReLU']:
        return nn.ReLU(inplace=True)
    elif name in ['lrelu', 'LReLU']:
        return nn.LeakyReLU(inplace=True)
    elif name in ['sigmoid', 'Sigmoid']:
        return nn.Sigmoid()
    elif name in ['softplus', 'Softplus']:
        return nn.Softplus(beta=4)
    elif name in ['celu', 'CeLU']:
        return nn.CELU()
    elif name in ['swish']:
        return Swish()
    else:
        raise ValueError('Unknown activation function')


'''class _ResLayer(nn.Module):
    def __init__(self, dim_in, dim_out, dim_hidden, act='tanh'):
        super().__init__()
        self.fc1 = nn.Linear(dim_in, dim_hidden)
        self.fc2 = nn.Linear(dim_hidden, dim_out)
        self.act = activation(act)

    def forward(self, x):
        # pre-activation
        res = x
        out = self.fc1(self.act(x))
        out = self.fc2(self.act(out))
        return res + out


class ResCPPN(nn.Sequential):

    def __init__(self, input_dimension, output_dimension, network_properties, act='tanh'):
        super().__init__()
        hidden_layers = int(network_properties["hidden_layers"])
        dim_hidden = int(network_properties["neurons"])
        self.lambda_residual = float(network_properties["residual_parameter"])
        self.kernel_regularizer = int(network_properties["kernel_regularizer"])
        self.regularization_param = float(network_properties["regularization_parameter"])
        self.num_epochs = int(network_properties["epochs"])
        self.optimizer = int(network_properties["optimizer"])

        reslayer = _ResLayer(dim_hidden, dim_hidden, dim_hidden, act=act)

        self.add_module('fc0', nn.Linear(input_dimension, dim_hidden))
        for i in range(hidden_layers):
            self.add_module(f'reslayer{i + 1}', reslayer)

        self.add_module('act_last', activation(act))
        self.add_module('fc_last', nn.Linear(dim_hidden, output_dimension))

    def _model_size(self):
        n_params, n_fc_layers = 0, 0
        for name, param in self.named_parameters():
            if 'fc' in name:
                n_fc_layers += 1
            n_params += param.numel()
        return n_params, n_fc_layers'''


class Pinns(nn.Module):

    def __init__(self, input_dimension, output_dimension, network_properties, additional_models=None,
                 solid_object=None):
        super(Pinns, self).__init__()
        # 1 input image channel, 6 output channels, 3x3 square convolution
        # kernel
        self.input_dimension = input_dimension
        self.output_dimension = output_dimension
        self.n_hidden_layers = int(network_properties["hidden_layers"])
        self.neurons = int(network_properties["neurons"])
        self.lambda_residual = float(network_properties["residual_parameter"])
        self.kernel_regularizer = int(network_properties["kernel_regularizer"])
        self.regularization_param = float(network_properties["regularization_parameter"])
        self.num_epochs = int(network_properties["epochs"])
        self.act_string = str(network_properties["activation"])
        self.optimizer = network_properties["optimizer"]

        self.input_layer = nn.Linear(self.input_dimension, self.neurons)
        self.batch_input = nn.BatchNorm1d(num_features=self.neurons, momentum=0.05)

        # self.hidden_layers = [nn.Linear(n_h, n_h) for _ in range(0, 3)]
        self.hidden_layers = nn.ModuleList(
            [nn.Linear(self.neurons, self.neurons) for _ in range(self.n_hidden_layers - 1)])
        self.batch_layers = nn.ModuleList([nn.BatchNorm1d(num_features=self.neurons, momentum=0.05) for _ in range(self.n_hidden_layers - 1)])
        self.output_layer = nn.Linear(self.neurons, self.output_dimension)

        self.solid_object = solid_object
        self.additional_models = additional_models

        self.activation = activation(self.act_string)
        # self.a = nn.Parameter(torch.randn((1,)))

    def forward(self, x):
        # x = torch.tanh(self.batch_input (self.input_layer(x)))
        # for b, l in zip(self.batch_layers, self.hidden_layers):
        #     x = torch.tanh(b(l(x)))
        # inputs = x
        # t = inputs[:, 0].reshape(-1, 1)
        # activation = nn.CELU()

        # activation = nn.ReLU()
        # print(self.a)

        x = self.activation(self.input_layer(x))
        for l in self.hidden_layers:
            x = self.activation(l(x))
        # x = self.activation(self.batch_input(self.input_layer(x)))
        # for b, l in zip(self.batch_layers, self.hidden_layers):
        #    x = self.activation(b(l(x)))

        # if self.solid_object is not None:
        #    im_in = self.solid_object.im_in(inputs)
        #    x[im_in, 0] = 0
        #    x[im_in, 1] = 0
        # x[im_in, 2] = 0

        # x[inputs[:, 0] == 0] = Ec.u0(inputs[inputs[:, 0] == 0,1])
        # x[inputs[:, 1] == -1]= Ec.ub0(inputs[inputs[:, 1] == -1,0])[0]
        # x[inputs[:, 1] == 1] = Ec.ub1(inputs[inputs[:, 1] == 1,0])[0]
        # if self.additional_models is not None and not isinstance(self.additional_models, list):
        #    return self.additional_models(inputs) + (t - Ec.extrema_values[0, 0]) * self.output_layer(x)
        # elif self.additional_models is not None and isinstance(self.additional_models, list):
        #    A = self.additional_models[0]
        #    B = self.additional_models[1]
        #    C = self.additional_models[2]
        #    # print(inputs,self.output_layer(x))
        #    print(torch.mean(A(inputs)), torch.mean(B(inputs)), torch.mean(C(inputs)), torch.mean(self.output_layer(x)))
        #    return A(inputs) + B(inputs) + C(inputs) * self.output_layer(x)
        # else:
        return self.output_layer(x)


def fit(model, training_set_class, validation_set_clsss=None, verbose=False, training_ic=False):
    num_epochs = model.num_epochs
    optimizer = model.optimizer

    train_losses = list([0, 0,0,0,0])
    val_losses = list()
    freq = 50

    training_coll = training_set_class.data_coll
    training_boundary = training_set_class.data_boundary
    training_initial_internal = training_set_class.data_initial_internal

    model.train()
    for epoch in range(num_epochs):  # loop over the dataset multiple times
        if verbose and epoch % freq == 0:
            print("################################ ", epoch, " ################################")

        print(len(training_boundary))
        print(len(training_coll))
        print(len(training_initial_internal))

        if len(training_boundary) != 0 and len(training_initial_internal) != 0:
            for step, ((x_coll_train_, u_coll_train_), (x_b_train_, u_b_train_), (x_u_train_, u_train_)) in enumerate(
                    zip(training_coll, training_boundary, training_initial_internal)):
                if verbose and epoch % freq == 0:
                    print("Batch Number:", step)

                x_ob = None
                u_ob = None

                if torch.cuda.is_available():
                    x_coll_train_ = x_coll_train_.cuda()
                    x_b_train_ = x_b_train_.cuda()
                    u_b_train_ = u_b_train_.cuda()
                    x_u_train_ = x_u_train_.cuda()
                    u_train_ = u_train_.cuda()

                def closure():
                    optimizer.zero_grad()
                    loss_f, loss_vars, loss_res, loss_reg, loss_wreg = CustomLoss()(model, x_u_train_, u_train_, x_b_train_, u_b_train_, x_coll_train_, x_ob, u_ob,
                                          training_set_class, training_ic)
                    loss_f.backward()
                    train_losses[0] = [loss_f, loss_vars, loss_res, loss_reg, loss_wreg]
                    # print(train_losses[0])
                    return loss_f

                optimizer.step(closure=closure)

                if torch.cuda.is_available():
                    del x_coll_train_
                    del x_b_train_
                    del u_b_train_
                    del x_u_train_
                    del u_train_
                    torch.cuda.empty_cache()
        elif len(training_boundary) == 0 and len(training_initial_internal) != 0:
            for step, ((x_coll_train_, u_coll_train_), (x_u_train_, u_train_)) in enumerate(zip(training_coll, training_initial_internal)):

                x_ob = None
                u_ob = None

                x_b_train_ = torch.full((4, 1), 0)
                u_b_train_ = torch.full((4, 1), 0)

                if torch.cuda.is_available():
                    x_coll_train_ = x_coll_train_.cuda()
                    x_b_train_ = x_b_train_.cuda()
                    u_b_train_ = u_b_train_.cuda()
                    x_u_train_ = x_u_train_.cuda()
                    u_train_ = u_train_.cuda()

                def closure():
                    optimizer.zero_grad()
                    loss_f = CustomLoss()(model, x_u_train_, u_train_, x_b_train_, u_b_train_, x_coll_train_, x_ob, u_ob,
                                          training_set_class, training_ic)
                    loss_f.backward()
                    train_losses[0] = loss_f
                    # print(train_losses[0])
                    return loss_f

                optimizer.step(closure=closure)

                if torch.cuda.is_available():
                    del x_coll_train_
                    del x_b_train_
                    del u_b_train_
                    del x_u_train_
                    del u_train_
                    torch.cuda.empty_cache()
        elif len(training_boundary) != 0 and len(training_initial_internal) == 0:
            for step, ((x_coll_train_, u_coll_train_), (x_b_train_, u_b_train_)) in enumerate(zip(training_coll, training_boundary)):

                x_ob = None
                u_ob = None

                x_u_train_ = torch.full((0, 1), 0)
                u_train_ = torch.full((0, 1), 0)

                if torch.cuda.is_available():
                    x_coll_train_ = x_coll_train_.cuda()
                    x_b_train_ = x_b_train_.cuda()
                    u_b_train_ = u_b_train_.cuda()
                    x_u_train_ = x_u_train_.cuda()
                    u_train_ = u_train_.cuda()

                def closure():
                    optimizer.zero_grad()
                    loss_f = CustomLoss()(model, x_u_train_, u_train_, x_b_train_, u_b_train_, x_coll_train_, x_ob, u_ob,
                                          training_set_class, training_ic)
                    loss_f.backward()
                    train_losses[0] = loss_f
                    # print(train_losses[0])
                    return loss_f

                optimizer.step(closure=closure)

                if torch.cuda.is_available():
                    del x_coll_train_
                    del x_b_train_
                    del u_b_train_
                    del x_u_train_
                    del u_train_
                    torch.cuda.empty_cache()

        if validation_set_clsss is not None:

            N_coll_val = validation_set_clsss.n_collocation
            N_b_val = validation_set_clsss.n_boundary
            validation_set = validation_set_clsss.data_no_batches

            for x_val, y_val in validation_set:
                model.eval()

                x_coll_val = x_val[:N_coll_val, :]
                x_b_val = x_val[N_coll_val:N_coll_val + 2 * validation_set_clsss.space_dimensions * N_b_val, :]
                u_b_val = y_val[N_coll_val:N_coll_val + 2 * validation_set_clsss.space_dimensions * N_b_val]
                x_u_val = x_val[N_coll_val:N_coll_val + 2 * validation_set_clsss.space_dimensions * N_b_val:, :]
                u_val = y_val[N_coll_val:N_coll_val + 2 * validation_set_clsss.space_dimensions * N_b_val:, :]

                if torch.cuda.is_available():
                    x_coll_val = x_coll_val.cuda()
                    x_b_val = x_b_val.cuda()
                    u_b_val = u_b_val.cuda()
                    x_u_val = x_u_val.cuda()
                    u_val = u_val.cuda()

                loss_val = CustomLoss()(model, x_u_val, u_val, x_b_val, u_b_val, x_coll_val, validation_set_clsss)

                if torch.cuda.is_available():
                    del x_coll_val
                    del x_b_val
                    del u_b_val
                    del x_u_val
                    del u_val
                    torch.cuda.empty_cache()

                    # val_losses.append(loss_val)
                if verbose and epoch % 100 == 0:
                    print("Validation Loss:", loss_val)

    history = [train_losses, val_losses] if validation_set_clsss is not None else [train_losses]

    return train_losses[0]


class CustomLoss(torch.nn.Module):

    def __init__(self):
        super(CustomLoss, self).__init__()

    def forward(self, network, x_u_train, u_train, x_b_train, u_b_train, x_f_train, x_obj, u_obj, dataclass,
                training_ic, computing_error=False):

        lambda_residual = network.lambda_residual
        lambda_reg = network.regularization_param
        order_regularizer = network.kernel_regularizer
        space_dimensions = dataclass.space_dimensions
        BC = dataclass.BC
        solid_object = dataclass.obj

        if x_b_train.shape[0] <= 1:
            space_dimensions = 0

        u_pred_var_list = list()
        u_train_var_list = list()
        for j in range(dataclass.output_dimension):
            # Space dimensions
            if not training_ic and Ec.extrema_values is not None:
                for i in range(space_dimensions):
                    half_len_x_b_train_i = int(x_b_train.shape[0] / (2 * space_dimensions))

                    x_b_train_i = x_b_train[i * int(x_b_train.shape[0] / space_dimensions):(i + 1) * int(
                        x_b_train.shape[0] / space_dimensions), :]
                    u_b_train_i = u_b_train[i * int(x_b_train.shape[0] / space_dimensions):(i + 1) * int(
                        x_b_train.shape[0] / space_dimensions), :]
                    boundary = 0
                    while boundary < 2:

                        x_b_train_i_half = x_b_train_i[
                                           half_len_x_b_train_i * boundary:half_len_x_b_train_i * (boundary + 1), :]
                        u_b_train_i_half = u_b_train_i[
                                           half_len_x_b_train_i * boundary:half_len_x_b_train_i * (boundary + 1), :]

                        if BC[i][boundary][j] == "func":
                            u_pred_var_list.append(network(x_b_train_i_half)[:, j])
                            u_train_var_list.append(u_b_train_i_half[:, j])
                        if BC[i][boundary][j] == "der":
                            x_b_train_i_half.requires_grad = True
                            f_val = network(x_b_train_i_half)[:, j]
                            inputs = torch.ones(x_b_train_i_half.shape[0], )
                            if not computing_error and torch.cuda.is_available():
                                inputs = inputs.cuda()
                            der_f_vals = torch.autograd.grad(f_val, x_b_train_i_half, grad_outputs=inputs, create_graph=True)[0][:, i]
                            u_pred_var_list.append(der_f_vals)
                            u_train_var_list.append(u_b_train_i_half[:, j])
                        elif BC[i][boundary][j] == "periodic":
                            x_half_1 = x_b_train_i_half
                            x_half_2 = x_b_train_i[
                                       half_len_x_b_train_i * (boundary + 1):half_len_x_b_train_i * (boundary + 2), :]
                            x_half_1.requires_grad = True
                            x_half_2.requires_grad = True
                            inputs = torch.ones(x_half_1.shape[0], )
                            if not computing_error and torch.cuda.is_available():
                                inputs = inputs.cuda()
                            pred_first_half = network(x_half_1)[:, j]
                            pred_second_half = network(x_half_2)[:, j]
                            der_pred_first_half = torch.autograd.grad(pred_first_half, x_half_1, grad_outputs=inputs, create_graph=True)[0]
                            der_pred_first_half_i = der_pred_first_half[:, i]
                            der_pred_second_half = torch.autograd.grad(pred_second_half, x_half_2, grad_outputs=inputs, create_graph=True)[0]
                            der_pred_second_half_i = der_pred_second_half[:, i]

                            u_pred_var_list.append(pred_second_half)
                            u_train_var_list.append(pred_first_half)

                            u_pred_var_list.append(der_pred_second_half_i)
                            u_train_var_list.append(der_pred_first_half_i)

                            boundary = boundary + 1

                        elif BC[i][boundary][j] == "wall":
                            x_b_train_i_half.requires_grad = True
                            inputs = torch.ones(x_b_train_i_half.shape[0], )
                            if not computing_error and torch.cuda.is_available():
                                inputs = inputs.cuda()
                            if j == 0:
                                zeros = torch.tensor(()).new_full(size=(x_b_train_i_half.shape[0],), fill_value=0.0)
                                ones = torch.tensor(()).new_full(size=(x_b_train_i_half.shape[0],), fill_value=1.0)

                                if not computing_error and torch.cuda.is_available():
                                    zeros = zeros.cuda()
                                    ones = ones.cuda()

                                phi = network(x_b_train_i_half)[:, 0]
                                u_pred_var_list.append(phi)
                                u_train_var_list.append(zeros)

                                grad_phi_i = torch.autograd.grad(phi, x_b_train_i_half, grad_outputs=inputs, create_graph=True)[0][:, i]
                                if i == 1 and boundary == 1:
                                    u_pred_var_list.append(grad_phi_i)
                                    u_train_var_list.append(ones)
                                else:
                                    u_pred_var_list.append(grad_phi_i)
                                    u_train_var_list.append(zeros)

                        boundary = boundary + 1
            else:
                u_pred_b, u_train_b = Ec.apply_BC(x_b_train, u_b_train, network)
                u_pred_var_list.append(u_pred_b)
                u_train_var_list.append(u_train_b)

                if Ec.time_dimensions != 0:
                    u_pred_0, u_train_0 = Ec.apply_IC(x_u_train, u_train, network)
                    u_pred_var_list.append(u_pred_0)
                    u_train_var_list.append(u_train_0)

            # Time Dimension
            if x_u_train.shape[0] != 0:
                try:
                    if j == 0:
                        if Ec.assign_g:
                            # print("Assign G")
                            g = Ec.get_G(network, x_u_train[:, :3], Ec.n_quad)
                            u_pred_var_list.append(g)

                        else:
                            # print("Not assign G")
                            u_pred_var_list.append(network(x_u_train)[:, j])
                        u_train_var_list.append(u_train[:, j])
                    if j == 1:
                        # print(x_b_train)
                        phys_coord_b = x_b_train[:, :3]
                        if Ec.average:
                            u_pred_var_list.append(Ec.get_average_inf_q(network, phys_coord_b, 10))
                        else:
                            u_pred_var_list.append(network(x_b_train)[:, j])
                        u_train_var_list.append(Ec.K(phys_coord_b[:, 0], phys_coord_b[:, 1], phys_coord_b[:, 2]))
                        # Compute tikonov regularization

                        x_f_train.requires_grad = True
                        k = network(x_f_train)[:, j].reshape(-1, )
                        lambda_k = 0.01

                        grad_k = torch.autograd.grad(k, x_f_train, grad_outputs=torch.ones(x_f_train.shape[0], ).to(Ec.dev), create_graph=True)[0]

                        grad_k_x = grad_k[:, 0]
                        grad_k_y = grad_k[:, 1]

                        tik_reg = torch.sqrt(lambda_k * torch.mean(grad_k_x ** 2 + grad_k_y ** 2)).reshape(1, )

                        u_pred_var_list.append(tik_reg)
                        u_train_var_list.append(torch.zeros_like(tik_reg))


                except AttributeError:
                    u_pred_var_list.append(network(x_u_train)[:, j])
                    u_train_var_list.append(u_train[:, j])

            if x_obj is not None and not training_ic:
                if BC[-1][j] == "func":
                    u_pred_var_list.append(network(x_obj)[:, j])
                    u_train_var_list.append(u_obj[:, j])

                if BC[-1][j] == "der":
                    x_obj_grad = x_obj.clone()
                    x_obj_transl = x_obj_grad[(np.arange(0, x_obj_grad.shape[0]) + 1) % (x_obj_grad.shape[0]), :]
                    x_obj_mean = (x_obj_grad + x_obj_transl) / 2
                    x_obj_mean.requires_grad = True
                    f_val = network(x_obj_mean)[:, j]
                    inputs = torch.ones(x_obj_mean.shape[0], )
                    if not computing_error and torch.cuda.is_available():
                        inputs = inputs.cuda()
                    der_f_vals_x = torch.autograd.grad(f_val, x_obj_mean, grad_outputs=inputs, create_graph=True)[0][:,
                                   0]
                    der_f_vals_y = torch.autograd.grad(f_val, x_obj_mean, grad_outputs=inputs, create_graph=True)[0][:,
                                   1]
                    t = (x_obj_grad - x_obj_transl)

                    nx = t[:, 1] / torch.sqrt(t[:, 1] ** 2 + t[:, 0] ** 2)
                    ny = -t[:, 0] / torch.sqrt(t[:, 1] ** 2 + t[:, 0] ** 2)

                    der_n = der_f_vals_x * nx + der_f_vals_y * ny
                    u_pred_var_list.append(der_n)
                    u_train_var_list.append(u_obj[:, j])

        u_pred_tot_vars = torch.cat(u_pred_var_list, 0)
        u_train_tot_vars = torch.cat(u_train_var_list, 0)

        if not computing_error and torch.cuda.is_available():
            u_pred_tot_vars = u_pred_tot_vars.cuda()
            u_train_tot_vars = u_train_tot_vars.cuda()

        assert not torch.isnan(u_pred_tot_vars).any()

        loss_vars = (torch.mean(abs(u_pred_tot_vars - u_train_tot_vars) ** 2))

        if not training_ic:

            res = Ec.compute_res(network, x_f_train, space_dimensions, solid_object, computing_error)
            res_train = torch.tensor(()).new_full(size=(res.shape[0],), fill_value=0.0)

            if not computing_error and torch.cuda.is_available():
                res = res.cuda()
                res_train = res_train.cuda()

            loss_res = (torch.mean(abs(res) ** 2))

            u_pred_var_list.append(res)
            u_train_var_list.append(res_train)

        loss_reg = regularization(network, order_regularizer)
        if not training_ic:
            loss_v = torch.log10(
                loss_vars + lambda_residual * loss_res + lambda_reg * loss_reg)  # + lambda_reg/loss_reg
        else:
            loss_v = torch.log10(loss_vars + lambda_reg * loss_reg)
        print("final loss:", loss_v.detach().cpu().numpy().round(4), " ", torch.log10(loss_vars).detach().cpu().numpy().round(4), " ",
              torch.log10(loss_res).detach().cpu().numpy().round(4))
        return loss_v,\
               torch.log10(loss_vars),\
               torch.log10(loss_res),\
               torch.log10(loss_reg),\
               torch.log10(loss_vars + lambda_residual*loss_res) # Exclude Regularization


'''class ResLoss(torch.nn.Module):

    def __init__(self):
        super(ResLoss, self).__init__()

    def forward(self, network, x_u_train, u_train, x_b_train, u_b_train, x_f_train, x_obj, u_obj, dataclass,
                training_ic):
        space_dimensions = dataclass.space_dimensions
        solid_object = dataclass.obj

        u_pred_var_list = list()
        u_train_var_list = list()

        tot_x = torch.cat([x_f_train, x_u_train, x_b_train], 0)
        # plt.figure()
        # plt.scatter(tot_x[:, 0].detach().numpy(), tot_x[:, 1].detach().numpy())
        # plt.show()
        # quit()
        res = Ec.compute_res(network, tot_x, space_dimensions, solid_object)
        res_train = torch.tensor(()).new_full(size=(res.shape[0],), fill_value=0.0)

        if torch.cuda.is_available():
            res = res.cuda()
            res_train = res_train.cuda()

        loss_res = (torch.mean(abs(res) ** 2))

        u_pred_var_list.append(res)
        u_train_var_list.append(res_train)

        # u_pred_var_list.append(network(x_u_train).reshape(-1,))
        # u_train_var_list.append(torch.tensor(()).new_full(size=(x_u_train.shape[0],), fill_value=0.0))

        # u_pred_var_list.append(network(x_b_train).reshape(-1, ))
        # u_train_var_list.append(torch.tensor(()).new_full(size=(x_b_train.shape[0],), fill_value=0.0))

        u_pred = torch.cat(u_pred_var_list, 0)
        u_train = torch.cat(u_train_var_list, 0)

        if torch.cuda.is_available():
            res = res.cuda()

        loss_res = torch.log10(torch.mean(abs(u_pred - u_train) ** 2))

        print("final loss:", loss_res)
        return loss_res'''


def regularization(model, p):
    reg_loss = 0
    for name, param in model.named_parameters():
        if 'weight' in name:
            reg_loss = reg_loss + torch.norm(param, p)
    return reg_loss


def init_xavier(model):
    def init_weights(m):
        if type(m) == nn.Linear and m.weight.requires_grad and m.bias.requires_grad:
            gain = nn.init.calculate_gain('tanh')
            # gain = 1
            torch.nn.init.xavier_uniform_(m.weight, gain=gain)
            m.bias.data.fill_(0.0)

    model.apply(init_weights)


def compute_error(dataset, trained_model):
    training_coll = dataset.data_coll
    training_boundary = dataset.data_boundary
    training_initial_internal = dataset.data_initial_internal
    error_mean = 0
    n = 0
    if len(training_boundary) != 0 and len(training_initial_internal) != 0:
        for step, ((x_coll, u_coll_train_), (x_b, u_b), (x_u, u)) in enumerate(
                zip(training_coll, training_boundary, training_initial_internal)):
            x_ob = None
            u_ob = None
            loss = CustomLoss()(trained_model, x_u, u, x_b, u_b, x_coll, x_ob, u_ob, dataset, False, True)
            error = torch.sqrt(10 ** loss)
            error_mean = error_mean + error
            n = n + 1
        error_mean = error_mean / n
    if len(training_boundary) != 0 and len(training_initial_internal) == 0:
        for step, ((x_coll, u_coll_train_), (x_b, u_b)) in enumerate(
                zip(training_coll, training_boundary)):
            x_ob = None
            u_ob = None
            x_u = torch.full((0, 1), 0)
            u = torch.full((0, 1), 0)
            loss = CustomLoss()(trained_model, x_u, u, x_b, u_b, x_coll, x_ob, u_ob, dataset, False, True)
            error = torch.sqrt(10 ** loss)
            error_mean = error_mean + error
            n = n + 1
        error_mean = error_mean / n
    if len(training_boundary) == 0 and len(training_initial_internal) != 0:
        for step, ((x_coll, u_coll_train_), (x_u, u)) in enumerate(
                zip(training_coll, training_initial_internal)):
            x_ob = None
            u_ob = None
            x_b = torch.full((0, 1), 0)
            u_b = torch.full((0, 1), 0)

            loss = CustomLoss()(trained_model, x_u, u, x_b, u_b, x_coll, x_ob, u_ob, dataset, False, True)
            error = torch.sqrt(10 ** loss)
            error_mean = error_mean + error
            n = n + 1
        error_mean = error_mean / n
    return error_mean


def compute_error_nocoll(dataset, trained_model):
    training_initial_internal = dataset.data_initial_internal
    error_mean = 0
    n = 0
    for step, (x_u, u) in enumerate(training_initial_internal):
        loss = StandardLoss()(trained_model, x_u, u)
        error = torch.sqrt(10 ** loss)
        error_mean = error_mean + error
        n = n + 1
    error_mean = error_mean / n
    return error_mean


def trainpartmods(training_set_class, optimizer_list, model_list_name, model_list):
    # Not working with internal point as u_train is assumed to contain only IC data here!!!

    N_coll_train = training_set_class.n_collocation
    N_b_train = training_set_class.n_boundary
    N_train = training_set_class.n_samples
    N_train_initial = training_set_class.n_initial
    N_train_internal = training_set_class.n_internal
    batch_dim = training_set_class.batches

    training_set = training_set_class.data_no_batches

    for name, model, optimizer in zip(model_list_name, model_list, optimizer_list):
        print("#########################################")
        print("Training model ", name)

        num_epochs = model.num_epochs

        for epoch in range(num_epochs):  # loop over the dataset multiple times

            current_loss = 0
            # training_set_b = training_set_class.assemble_batches(epoch)
            training_coll = training_set_class.data_coll
            training_boundary = training_set_class.data_boundary
            training_initial_internal = training_set_class.data_initial_internal
            # for step, (x, y) in enumerate(training_set_b):
            for step, ((x_coll_train_, u_coll_train_), (x_b_train_, u_b_train_), (x_u_train_, u_train_)) in enumerate(
                    zip(training_coll, training_boundary, training_initial_internal)):

                outputs = u_b_train_.shape[1]

                if name == "A":
                    for i in range(outputs):
                        u_b_train_[:, i] = torch.tensor(()).new_full(size=(u_b_train_.shape[0],), fill_value=0.0)
                    input_train = torch.cat([x_u_train_, x_b_train_], 0)
                    output_train = torch.cat([u_train_, u_b_train_], 0)

                elif name == "B":
                    for i in range(outputs):
                        u_train_[:, i] = torch.tensor(()).new_full(size=(u_train_.shape[0],), fill_value=0.0)
                    input_train = torch.cat([x_u_train_, x_b_train_], 0)
                    output_train = torch.cat([u_train_, u_b_train_], 0)
                elif name == "C":
                    for i in range(outputs):
                        u_train_[:, i] = torch.tensor(()).new_full(size=(u_train_.shape[0],), fill_value=0.0)
                        u_b_train_[:, i] = torch.tensor(()).new_full(size=(u_b_train_.shape[0],), fill_value=0.0)
                    x = x_coll_train_[:, 1]
                    t = x_coll_train_[:, 0]
                    plt.scatter(t, x)
                    plt.show()
                    # quit()
                    interiorior_func = -(t) * (x - 1) * (x + 1)
                    # interiorior_func = interiorior_func/torch.mean(interiorior_func)
                    for i in range(outputs):
                        u_coll_train_[:, i] = interiorior_func  # *torch.mean(u_train_[:,i])
                    input_train = torch.cat([x_u_train_, x_b_train_, x_coll_train_], 0)
                    output_train = torch.cat([u_train_, u_b_train_, u_coll_train_], 0)
                    # input_train = torch.cat([x_u_train_, x_b_train_], 0)
                    # output_train = torch.cat([u_train_, u_b_train_], 0)
                print(input_train, output_train)
                if torch.cuda.is_available():
                    x_b_train_ = x_b_train_.cuda()
                    u_b_train_ = u_b_train_.cuda()
                    x_u_train_ = x_u_train_.cuda()
                    u_train_ = u_train_.cuda()

                def closure():
                    optimizer.zero_grad()
                    loss_f = StandardLoss()(model, input_train, output_train)
                    loss_f.backward()
                    return loss_f

                optimizer.step(closure=closure)

                if torch.cuda.is_available():
                    del x_b_train_
                    del u_b_train_
                    del x_u_train_
                    del u_train_
                    torch.cuda.empty_cache()


class StandardLoss(torch.nn.Module):
    def __init__(self):
        super(StandardLoss, self).__init__()

    def forward(self, network, x_u_train, u_train):
        loss_reg = regularization(network, 2)
        lambda_reg = network.regularization_param
        u_pred = network(x_u_train)

        '''x_u_train.requires_grad = True
        u = network(x_u_train).reshape(-1, )
        u_ex = torch.tensor(9.)/torch.cosh(np.sqrt(3.)/2*(x_u_train[:,1] - 3 * x_u_train[:,0]))**2
        grad_u = torch.autograd.grad(u, x_u_train, grad_outputs=torch.ones(x_u_train.shape[0], ), create_graph=True)[0]
        grad_u_t = grad_u[:, 0]
        grad_u_x = grad_u[:, 1]
        grad_u_xx = torch.autograd.grad(grad_u_x, x_u_train, grad_outputs=torch.ones(x_u_train.shape[0]), create_graph=True)[0][:, 1]
        grad_u_xxx = torch.autograd.grad(grad_u_xx, x_u_train, grad_outputs=torch.ones(x_u_train.shape[0]), create_graph=True)[0][:, 1]
        plt.scatter(x_u_train[:, 1].detach().numpy(), u.detach().numpy(), s=10)
        plt.scatter(x_u_train[:, 1].detach().numpy(), grad_u_x.detach().numpy(), s=10)
        plt.scatter(x_u_train[:, 1].detach().numpy(), grad_u_xx.detach().numpy(), s=10)
        plt.scatter(x_u_train[:, 1].detach().numpy(), grad_u_xxx.detach().numpy(), s=10)

        grad_u = torch.autograd.grad(u_ex, x_u_train, grad_outputs=torch.ones(x_u_train.shape[0], ), create_graph=True)[0]
        grad_u_t = grad_u[:, 0]
        grad_u_x = grad_u[:, 1]
        grad_u_xx = torch.autograd.grad(grad_u_x, x_u_train, grad_outputs=torch.ones(x_u_train.shape[0]), create_graph=True)[0][:, 1]
        grad_u_xxx = torch.autograd.grad(grad_u_xx, x_u_train, grad_outputs=torch.ones(x_u_train.shape[0]), create_graph=True)[0][:, 1]
        plt.scatter(x_u_train[:, 1].detach().numpy(), u_ex.detach().numpy(), s=10, marker="v")
        plt.scatter(x_u_train[:, 1].detach().numpy(), grad_u_x.detach().numpy(), s=10, marker="v")
        plt.scatter(x_u_train[:, 1].detach().numpy(), grad_u_xx.detach().numpy(), s=10, marker="v")
        plt.scatter(x_u_train[:, 1].detach().numpy(), grad_u_xxx.detach().numpy(), s=10, marker="v")
        plt.pause(0.0000001)
        plt.clf()'''
        loss = torch.log10(torch.mean((u_train - u_pred) ** 2) + lambda_reg * loss_reg)
        del u_train, u_pred
        print(loss)
        return loss


def StandardFit(model, training_set_class, validation_set_clsss=None, verbose=False):
    num_epochs = model.num_epochs
    optimizer = model.optimizer

    train_losses = list([np.nan])
    val_losses = list()
    freq = 4

    model.train()
    training_initial_internal = training_set_class.data_initial_internal
    for epoch in range(num_epochs):  # loop over the dataset multiple times
        if verbose and epoch % freq == 0:
            print("################################ ", epoch, " ################################")

        for step, (x_u_train_, u_train_) in enumerate(training_initial_internal):
            if verbose and epoch % freq == 0:
                print("Batch Number:", step)

            if torch.cuda.is_available():
                x_u_train_ = x_u_train_.cuda()
                u_train_ = u_train_.cuda()

            def closure():
                optimizer.zero_grad()
                loss_f = StandardLoss()(model, x_u_train_, u_train_)
                loss_f.backward()
                train_losses[0] = loss_f
                return loss_f

            optimizer.step(closure=closure)

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            del x_u_train_
            del u_train_

    history = [train_losses, val_losses] if validation_set_clsss is not None else [train_losses]

    return train_losses[0]
