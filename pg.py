import gym
import numpy as np
from keras.models import Sequential
from keras.layers import Dense, Reshape, Flatten
from keras.optimizers import Adam
from keras.layers.convolutional import Conv2D


class PGAgent:
    def __init__(self, state_size, action_size):
        self.state_size = state_size
        self.action_size = action_size
        self.gamma = 0.99
        self.learning_rate = 0.001
        self.states = []
        self.gradients = []
        self.rewards = []
        self.probs = []
        self.model = self._build_model()
        self.model.summary()

    def _build_model(self):
        model = Sequential()
        model.add(Reshape((1, 80, 80), input_shape=(self.state_size,)))
        model.add(Conv2D(32, (6, 6), strides=(3, 3), padding='same',
                                activation='relu'))
        model.add(Flatten())
        model.add(Dense(64, activation='relu'))
        model.add(Dense(32, activation='relu'))
        model.add(Dense(self.action_size, activation='softmax'))
        opt = Adam(lr=self.learning_rate)
        model.compile(loss='categorical_crossentropy', optimizer=opt)
        return model

    def memorize(self, state, action, prob, reward):
        y = np.zeros([self.action_size])
        y[action] = 1  # 目标是期望state-value（V(s;\theat)）更大，近似等价于策略函数中对应动作的概率最大；
        self.gradients.append(np.array(y).astype('float32') - prob)
        self.states.append(state)
        self.rewards.append(reward)

    def act(self, state):
        state = state.reshape([1, state.shape[0]])
        aprob = self.model.predict(state, batch_size=1).flatten()
        self.probs.append(aprob)
        prob = aprob / np.sum(aprob)  # isn't it stupid
        test_ =  np.random.choice(self.action_size,1,  p=prob)
        action = np.random.choice(self.action_size, 1, p=prob)[0]
        return action, prob

    def discount_rewards(self, rewards):
        discounted_rewards = np.zeros_like(rewards)
        running_add = 0
        for t in reversed(range(0, rewards.size)):
            if rewards[t] != 0:
                running_add = 0
            running_add = running_add * self.gamma + rewards[t]
            discounted_rewards[t] = running_add
        return discounted_rewards

    def train(self):
        gradients = np.vstack(self.gradients)
        rewards = np.vstack(self.rewards)
        rewards = self.discount_rewards(rewards)
        rewards = (rewards - np.mean(rewards)) / (np.std(rewards) + 1e-7)  # compute the rewards
        gradients *= rewards
        X = np.squeeze(np.vstack([self.states]))
        # gradients类似理解成目标概率与实际的差距，Y理解成修正的目标概率
        # 学习率是针对的概率差距的，使用的是交叉熵损失函数，衡量的是实际
        # 输出（概率）与期望输出（概率）的差距。
        # 我们没有重写损失函数，而是转换了taget为期望输出概率
        Y = self.probs + self.learning_rate * np.squeeze(np.vstack([gradients]))

        self.model.train_on_batch(X, Y)
        self.states, self.probs, self.gradients, self.rewards = [], [], [], []

    def load(self, name):
        self.model.load_weights(name)

    def save(self, name):
        self.model.save_weights(name)

def preprocess(I):
    I = I[35:195]
    I = I[::2, ::2, 0]
    I[I == 144] = 0
    I[I == 109] = 0
    I[I != 0] = 1
    return I.astype(np.float).ravel()

if __name__ == "__main__":
    env = gym.make("Pong-v0")
    state = env.reset()
    prev_x = None
    score = 0
    episode = 0

    state_size = 80 * 80
    action_size = env.action_space.n
    agent = PGAgent(state_size, action_size)
    agent.load('pong.h5')
    while True:
        env.render()

        cur_x = preprocess(state)
        x = cur_x - prev_x if prev_x is not None else np.zeros(state_size)
        prev_x = cur_x

        action, prob = agent.act(x)
        state, reward, done, info = env.step(action)
        score += reward
        agent.memorize(x, action, prob, reward)

        if done:
            episode += 1
            agent.train()
            print('Episode: %d - Score: %f.' % (episode, score))
            score = 0
            state = env.reset()
            prev_x = None
            if episode > 1 and episode % 10 == 0:
                agent.save('pong.h5')
