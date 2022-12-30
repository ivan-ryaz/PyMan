import pygame
import os
import numpy as np
from random import randint
twidth, theight = 16, 16
rows_, cols_ = 36, 28
screenw, screenh = cols_ * twidth, rows_ * theight
SCREENSIZE = screenw, screenh
stop = 0
up, down, left, right = 1, -1, 2, -2
port = 3
PACMAN = 0
PELLET = 1
POWERPELLET = 2
GHOST = 3
bli = 4
pin = 5
ink = 6
cly = 7
fru = 8
SCATTER = 0
CHASE = 1
FREIGHT = 2
SPAWN = 3
SCORETXT = 0
LEVELTXT = 1
READYTXT = 2
PAUSETXT = 3
GAMEOVERTXT = 4
BASETILEWIDTH = 16
BASETILEHEIGHT = 16
DEATH = 5


class Animator(object):
    def __init__(self, frames=[], speed=20, loop=True):
        self.frames = frames
        self.current_frame = 0
        self.speed = speed
        self.loop = loop
        self.dt = 0
        self.finished = False

    def reset(self):
        self.current_frame = 0
        self.finished = False

    def update(self, dt):
        if not self.finished:
            self.nextFrame(dt)
        if self.current_frame == len(self.frames):
            if self.loop:
                self.current_frame = 0
            else:
                self.finished = True
                self.current_frame -= 1
        return self.frames[self.current_frame]

    def nextFrame(self, dt):
        self.dt += dt
        if self.dt >= (1.0 / self.speed):
            self.current_frame += 1
            self.dt = 0


class Entity(object):
    def __init__(self, node):
        self.name = None
        self.directions = {up: vec(0, -1), down: vec(0, 1),
                           left: vec(-1, 0), right: vec(1, 0), stop: vec()}
        self.direction = stop
        self.setSpeed(100)
        self.rad = 10
        self.colrad = 5
        self.color = (255, 255, 255)
        self.visible = True
        self.disablePortal = False
        self.goal = None
        self.directionMethod = self.randomDirection
        self.setStartNode(node)
        self.image = None

    def setPosition(self):
        self.position = self.node.position.copy()

    def update(self, dt):
        self.position += self.directions[self.direction] * self.speed * dt
        if self.overshotTarget():
            self.node = self.target
            directions = self.validDirections()
            direction = self.directionMethod(directions)
            if not self.disablePortal:
                if self.node.neighbors[port] is not None:
                    self.node = self.node.neighbors[port]
            self.target = self.getNewTarget(direction)
            if self.target is not self.node:
                self.direction = direction
            else:
                self.target = self.getNewTarget(self.direction)
            self.setPosition()

    def validDirection(self, direction):
        return direction is not stop and self.name in self.node.access[direction] and \
               self.node.neighbors[direction] is not None

    def getNewTarget(self, direction):
        if self.validDirection(direction):
            return self.node.neighbors[direction]
        return self.node

    def overshotTarget(self):
        if self.target is not None:
            vec1 = self.target.position - self.node.position
            vec2 = self.position - self.node.position
            node2Target = vec1.magnitudeSquared()
            node2Self = vec2.magnitudeSquared()
            return node2Self >= node2Target
        return False

    def reverseDirection(self):
        self.direction *= -1
        temp = self.node
        self.node = self.target
        self.target = temp

    def oppositeDirection(self, direction):
        return direction is not stop and direction == self.direction * -1

    def validDirections(self):
        directions = []
        for key in [up, down, left, right]:
            if self.validDirection(key):
                if key != self.direction * -1:
                    directions.append(key)
        if len(directions) == 0:
            directions.append(self.direction * -1)
        return directions

    def randomDirection(self, directions):
        return directions[randint(0, len(directions) - 1)]

    def goalDirection(self, directions):
        distances = []
        for direction in directions:
            vec = self.node.position + self.directions[direction] * twidth - self.goal
            distances.append(vec.magnitudeSquared())
        index = distances.index(min(distances))
        return directions[index]

    def setStartNode(self, node):
        self.node = node
        self.startNode = node
        self.target = node
        self.setPosition()

    def setBetweenNodes(self, direction):
        if self.node.neighbors[direction] is not None:
            self.target = self.node.neighbors[direction]
            self.position = (self.node.position + self.target.position) / 2.0

    def reset(self):
        self.setStartNode(self.startNode)
        self.direction = stop
        self.speed = 100
        self.visible = True

    def setSpeed(self, speed):
        self.speed = speed * twidth / 16

    def render(self, screen):
        if self.visible:
            if self.image is not None:
                p = self.position - vec(twidth, theight) / 2
                screen.blit(self.image, p.asTuple())
            else:
                p = self.position.asInt()
                pygame.draw.circle(screen, self.color, p, self.rad)


class Fruit(Entity):
    def __init__(self, node, level=0):
        Entity.__init__(self, node)
        self.name = fru
        self.color = (0, 255, 0)
        self.lifespan = 10
        self.timer = 0
        self.destroy = False
        self.points = 100 + level * 20
        self.setBetweenNodes(right)
        self.sprites = FruitSprites(self, level)

    def update(self, dt):
        self.timer += dt
        if self.timer >= self.lifespan:
            self.destroy = True


class Ghost(Entity):
    def __init__(self, node, pacman=None, blinky=None):
        Entity.__init__(self, node)
        self.name = GHOST
        self.points = 200
        self.goal = vec()
        self.directionMethod = self.goalDirection
        self.pacman = pacman
        self.mode = ModeController(self)
        self.blinky = blinky
        self.homeNode = node

    def reset(self):
        Entity.reset(self)
        self.points = 200
        self.directionMethod = self.goalDirection

    def update(self, dt):
        self.sprites.update(dt)
        self.mode.update(dt)
        if self.mode.cur is SCATTER:
            self.scatter()
        elif self.mode.cur is CHASE:
            self.chase()
        Entity.update(self, dt)

    def scatter(self):
        self.goal = vec()

    def chase(self):
        self.goal = self.pacman.position

    def spawn(self):
        self.goal = self.spawnNode.position

    def setSpawnNode(self, node):
        self.spawnNode = node

    def startSpawn(self):
        self.mode.setSpawnMode()
        if self.mode.cur == SPAWN:
            self.setSpeed(150)
            self.directionMethod = self.goalDirection
            self.spawn()

    def startFreight(self):
        self.mode.setFreightMode()
        if self.mode.cur == FREIGHT:
            self.setSpeed(50)
            self.directionMethod = self.randomDirection

    def normalMode(self):
        self.setSpeed(100)
        self.directionMethod = self.goalDirection
        self.homeNode.denyAccess(down, self)


class Blinky(Ghost):
    def __init__(self, node, pacman=None, blinky=None):
        Ghost.__init__(self, node, pacman, blinky)
        self.name = bli
        self.color = (255, 0, 0)
        self.sprites = GhostSprites(self)


class Pinky(Ghost):
    def __init__(self, node, pacman=None, blinky=None):
        Ghost.__init__(self, node, pacman, blinky)
        self.name = pin
        self.color = (255, 100, 150)
        self.sprites = GhostSprites(self)

    def scatter(self):
        self.goal = vec(twidth * cols_, 0)

    def chase(self):
        self.goal = self.pacman.position + self.pacman.directions[self.pacman.direction] * twidth * 4


class Inky(Ghost):
    def __init__(self, node, pacman=None, blinky=None):
        Ghost.__init__(self, node, pacman, blinky)
        self.name = ink
        self.color = (100, 255, 255)
        self.sprites = GhostSprites(self)

    def scatter(self):
        self.goal = vec(twidth * cols_, theight * rows_)

    def chase(self):
        vec1 = self.pacman.position + self.pacman.directions[self.pacman.direction] * twidth * 2
        vec2 = (vec1 - self.blinky.position) * 2
        self.goal = self.blinky.position + vec2


class Clyde(Ghost):
    def __init__(self, node, pacman=None, blinky=None):
        Ghost.__init__(self, node, pacman, blinky)
        self.name = cly
        self.color = (230, 190, 40)
        self.sprites = GhostSprites(self)

    def scatter(self):
        self.goal = vec(0, theight * rows_)

    def chase(self):
        d = self.pacman.position - self.position
        ds = d.magnitudeSquared()
        if ds <= (twidth * 8) ** 2:
            self.scatter()
        else:
            self.goal = self.pacman.position + self.pacman.directions[self.pacman.direction] * twidth * 4


class GhostGroup(object):
    def __init__(self, node, pacman):
        self.blinky = Blinky(node, pacman)
        self.pinky = Pinky(node, pacman)
        self.inky = Inky(node, pacman, self.blinky)
        self.clyde = Clyde(node, pacman)
        self.ghosts = [self.blinky, self.pinky, self.inky, self.clyde]

    def __iter__(self):
        return iter(self.ghosts)

    def update(self, dt):
        [ghost.update(dt) for ghost in self]

    def startFreight(self):
        [ghost.startFreight() for ghost in self]
        self.resetPoints()

    def setSpawnNode(self, node):
        [ghost.setSpawnNode(node) for ghost in self]

    def updatePoints(self):
        for ghost in self:
            ghost.points *= 2

    def resetPoints(self):
        for ghost in self:
            ghost.points = 200

    def hide(self):
        for ghost in self:
            ghost.visible = False

    def show(self):
        for ghost in self:
            ghost.visible = True

    def reset(self):
        [ghost.reset() for ghost in self]

    def render(self, screen):
        [ghost.render(screen) for ghost in self]


def checkEv(self):
    for event in pygame.event.get():
        if event.type == QUIT:
            exit()
        elif event.type == KEYDOWN:
            if event.key == K_SPACE:
                if self.pacman.alive:
                    self.pause.setPause(playerPaused=True)
                    if not self.pause.paused:
                        self.showEntities()
                    else:
                        self.hideEntities()


class MazeBase(object):
    def __init__(self):
        self.portalPairs = {}
        self.homeoffset = (0, 0)
        self.ghostNodeDeny = {up: (), down: (), left: (), right: ()}

    def setPortalPairs(self, nodes):
        [nodes.setPortalPair(*pair) for pair in list(self.portalPairs.values())]

    def conHomnod(self, nodes):
        key = nodes.createHomeNodes(*self.homeoffset)
        nodes.conHomnod(key, self.homenodeconnectLeft, left)
        nodes.conHomnod(key, self.homenodeconnectRight, right)

    def addOffset(self, x, y):
        return x + self.homeoffset[0], y + self.homeoffset[1]

    def GhostsA(self, ghosts, nodes):
        nodes.denyAccessList(*(self.addOffset(2, 3) + (left, ghosts)))
        nodes.denyAccessList(*(self.addOffset(2, 3) + (right, ghosts)))
        for direction in list(self.ghostNodeDeny.keys()):
            for values in self.ghostNodeDeny[direction]:
                nodes.denyAccessList(*(values + (direction, ghosts)))


class Maze1(MazeBase):
    def __init__(self):
        MazeBase.__init__(self)
        self.name = 'maze1'
        self.portalPairs = {0: ((0, 17), (27, 17))}
        self.homeoffset = (11.5, 14)
        self.homenodeconnectLeft = (12, 14)
        self.homenodeconnectRight = (15, 14)
        self.pacmanStart = (15, 26)
        self.fruitStart = (9, 20)
        self.ghostNodeDeny = {up: ((12, 14), (15, 14), (12, 26), (15, 26)), left: (self.addOffset(2, 3),),
                              right: (self.addOffset(2, 3),)}


class Maze2(MazeBase):
    def __init__(self):
        MazeBase.__init__(self)
        self.name = 'maze2'
        self.portalPairs = {0: ((0, 4), (27, 4)), 1: ((0, 26), (27, 26))}
        self.homeoffset = (11.5, 14)
        self.homenodeconnectLeft = (9, 14)
        self.homenodeconnectRight = (18, 14)
        self.pacmanStart = (16, 26)
        self.fruitStart = (11, 20)
        self.ghostNodeDeny = {up: ((9, 14), (18, 14), (11, 23), (16, 23)), left: (self.addOffset(2, 3),),
                              right: (self.addOffset(2, 3),)}


class MainMode(object):
    def __init__(self):
        self.timer = 0
        self.scatter()

    def update(self, dt):
        self.timer += dt
        if self.timer >= self.time:
            if self.mode is SCATTER:
                self.chase()
            elif self.mode is CHASE:
                self.scatter()

    def scatter(self):
        self.mode = SCATTER
        self.time = 7
        self.timer = 0

    def chase(self):
        self.mode = CHASE
        self.time = 20
        self.timer = 0


class ModeController(object):
    def __init__(self, entity):
        self.timer = 0
        self.time = None
        self.mainmode = MainMode()
        self.cur = self.mainmode.mode
        self.entity = entity

    def update(self, dt):
        self.mainmode.update(dt)
        if self.cur is FREIGHT:
            self.timer += dt
            if self.timer >= self.time:
                self.time = None
                self.entity.normalMode()
                self.cur = self.mainmode.mode
        elif self.cur in [SCATTER, CHASE]:
            self.cur = self.mainmode.mode
        if self.cur is SPAWN:
            if self.entity.node == self.entity.spawnNode:
                self.entity.normalMode()
                self.cur = self.mainmode.mode

    def setFreightMode(self):
        if self.cur in [SCATTER, CHASE]:
            self.timer = 0
            self.time = 7
            self.cur = FREIGHT
        elif self.cur is FREIGHT:
            self.timer = 0

    def setSpawnMode(self):
        if self.cur is FREIGHT:
            self.cur = SPAWN


class MazeData(object):
    def __init__(self):
        self.obj = None
        self.mazedict = {0: Maze1, 1: Maze2}

    def loadMaze(self, level):
        self.obj = self.mazedict[level % len(self.mazedict)]()


class Node(object):
    def __init__(self, x, y):
        self.position = vec(x, y)
        self.neighbors = {up: None, down: None, left: None, right: None, port: None}
        self.access = {up: [PACMAN, bli, pin, ink, cly, fru],
                       down: [PACMAN, bli, pin, ink, cly, fru],
                       left: [PACMAN, bli, pin, ink, cly, fru],
                       right: [PACMAN, bli, pin, ink, cly, fru]}

    def denyAccess(self, direction, entity):
        if entity.name in self.access[direction]:
            self.access[direction].remove(entity.name)

    def allowAccess(self, direction, entity):
        if entity.name not in self.access[direction]:
            self.access[direction].append(entity.name)

    def render(self, screen):
        for n in self.neighbors.keys():
            if self.neighbors[n] is not None:
                line_start = self.position.asTuple()
                line_end = self.neighbors[n].position.asTuple()
                pygame.draw.line(screen, (255, 255, 255), line_start, line_end, 4)
                pygame.draw.circle(screen, (255, 0, 0), self.position.asInt(), 12)


class NodeG(object):
    def __init__(self, level):
        self.level = level
        self.nodesLUT = {}
        self.nodeSymbols = ['+', 'P', 'n']
        self.pathSymbols = ['.', '-', '|', 'p']
        data = self.readmz(level)
        self.createNodeTable(data)
        self.connectHorizontally(data)
        self.connectVertically(data)
        self.homekey = None

    def readmz(self, textfile):
        return np.loadtxt(textfile, dtype='<U1')

    def createNodeTable(self, data, xoffset=0, yoffset=0):
        for row in list(range(data.shape[0])):
            for col in list(range(data.shape[1])):
                if data[row][col] in self.nodeSymbols:
                    x, y = self.constructKey(col + xoffset, row + yoffset)
                    self.nodesLUT[(x, y)] = Node(x, y)

    def constructKey(self, x, y):
        return x * twidth, y * theight

    def connectHorizontally(self, data, xoffset=0, yoffset=0):
        for row in list(range(data.shape[0])):
            key = None
            for col in list(range(data.shape[1])):
                if data[row][col] in self.nodeSymbols:
                    if key is None:
                        key = self.constructKey(col + xoffset, row + yoffset)
                    else:
                        otherkey = self.constructKey(col + xoffset, row + yoffset)
                        self.nodesLUT[key].neighbors[right] = self.nodesLUT[otherkey]
                        self.nodesLUT[otherkey].neighbors[left] = self.nodesLUT[key]
                        key = otherkey
                elif data[row][col] not in self.pathSymbols:
                    key = None

    def connectVertically(self, data, xoffset=0, yoffset=0):
        dataT = data.transpose()
        for col in list(range(dataT.shape[0])):
            key = None
            for row in list(range(dataT.shape[1])):
                if dataT[col][row] in self.nodeSymbols:
                    if key is None:
                        key = self.constructKey(col + xoffset, row + yoffset)
                    else:
                        otherkey = self.constructKey(col + xoffset, row + yoffset)
                        self.nodesLUT[key].neighbors[down] = self.nodesLUT[otherkey]
                        self.nodesLUT[otherkey].neighbors[up] = self.nodesLUT[key]
                        key = otherkey
                elif dataT[col][row] not in self.pathSymbols:
                    key = None

    def getStartTempNode(self):
        return list(self.nodesLUT.values())[0]

    def setPortalPair(self, pair1, pair2):
        key1 = self.constructKey(*pair1)
        key2 = self.constructKey(*pair2)
        if key1 in self.nodesLUT.keys() and key2 in self.nodesLUT.keys():
            self.nodesLUT[key1].neighbors[port] = self.nodesLUT[key2]
            self.nodesLUT[key2].neighbors[port] = self.nodesLUT[key1]

    def createHomeNodes(self, xoffset, yoffset):
        homedata = np.array([['X', 'X', '+', 'X', 'X'], ['X', 'X', '.', 'X', 'X'],
                             ['+', 'X', '.', 'X', '+'], ['+', '.', '+', '.', '+'],
                             ['+', 'X', 'X', 'X', '+']])
        self.createNodeTable(homedata, xoffset, yoffset)
        self.connectHorizontally(homedata, xoffset, yoffset)
        self.connectVertically(homedata, xoffset, yoffset)
        self.homekey = self.constructKey(xoffset + 2, yoffset)
        return self.homekey

    def conHomnod(self, homekey, otherkey, direction):
        key = self.constructKey(*otherkey)
        self.nodesLUT[homekey].neighbors[direction] = self.nodesLUT[key]
        self.nodesLUT[key].neighbors[direction * -1] = self.nodesLUT[homekey]

    def getNodeFromPixels(self, xpixel, ypixel):
        if (xpixel, ypixel) in self.nodesLUT.keys():
            return self.nodesLUT[(xpixel, ypixel)]
        return

    def getNodeFromTiles(self, col, row):
        x, y = self.constructKey(col, row)
        if (x, y) in self.nodesLUT.keys():
            return self.nodesLUT[(x, y)]
        return

    def denyAccess(self, col, row, direction, entity):
        node = self.getNodeFromTiles(col, row)
        if node is not None:
            node.denyAccess(direction, entity)

    def allowAccess(self, col, row, direction, entity):
        node = self.getNodeFromTiles(col, row)
        if node is not None:
            node.allowAccess(direction, entity)

    def denyAccessList(self, col, row, direction, entities):
        for entity in entities:
            self.denyAccess(col, row, direction, entity)

    def allowAccessList(self, col, row, direction, entities):
        for entity in entities:
            self.allowAccess(col, row, direction, entity)

    def denyHomeAccess(self, entity):
        self.nodesLUT[self.homekey].denyAccess(down, entity)

    def allowHomeAccess(self, entity):
        self.nodesLUT[self.homekey].allowAccess(down, entity)

    def denyHomeAccessList(self, ent):
        [self.denyHomeAccess(i) for i in ent]

    def allowHomeAccessList(self, entities):
        for entity in entities:
            self.allowHomeAccess(entity)

    def render(self, screen):
        for node in self.nodesLUT.values():
            node.render(screen)


class Pacman(Entity):
    def __init__(self, node):
        Entity.__init__(self, node)
        self.name = PACMAN
        self.color = (255, 255, 0)
        self.direction = left
        self.setBetweenNodes(left)
        self.alive = True
        self.sprites = PacmanSprites(self)

    def reset(self):
        Entity.reset(self)
        self.direction = left
        self.setBetweenNodes(left)
        self.alive = True
        self.image = self.sprites.getStartImage()
        self.sprites.reset()

    def die(self):
        self.alive = False
        self.direction = stop

    def update(self, dt):
        self.sprites.update(dt)
        self.position += self.directions[self.direction] * self.speed * dt
        direction = self.getValidKey()
        if self.overshotTarget():
            self.node = self.target
            if self.node.neighbors[port] is not None:
                self.node = self.node.neighbors[port]
            self.target = self.getNewTarget(direction)
            if self.target is not self.node:
                self.direction = direction
            else:
                self.target = self.getNewTarget(self.direction)

            if self.target is self.node:
                self.direction = stop
            self.setPosition()
        else:
            if self.oppositeDirection(direction):
                self.reverseDirection()

    def getValidKey(self):
        key_pressed = pygame.key.get_pressed()
        if key_pressed[pygame.K_UP] or key_pressed[pygame.K_w]:
            return up
        if key_pressed[pygame.K_DOWN] or key_pressed[pygame.K_s]:
            return down
        if key_pressed[pygame.K_LEFT] or key_pressed[pygame.K_a]:
            return left
        if key_pressed[pygame.K_RIGHT] or key_pressed[pygame.K_d]:
            return right
        return stop

    def eatPellets(self, pellist):
        for pellet in pellist:
            if self.collideCheck(pellet):
                return pellet
        return

    def collideGhost(self, ghost):
        return self.collideCheck(ghost)

    def collideCheck(self, other):
        d = self.position - other.position
        dSquared = d.magnitudeSquared()
        rSquared = (self.colrad + other.colrad) ** 2
        return dSquared <= rSquared


class Pause(object):
    def __init__(self, paused=False):
        self.paused = paused
        self.timer = 0
        self.pauseTime = None
        self.func = None

    def update(self, dt):
        if self.pauseTime is not None:
            self.timer += dt
            if self.timer >= self.pauseTime:
                self.timer = 0
                self.paused = False
                self.pauseTime = None
                return self.func
        return

    def setPause(self, playerPaused=False, pauseTime=None, func=None):
        self.timer = 0
        self.func = func
        self.pauseTime = pauseTime
        self.flip()

    def flip(self):
        self.paused = not self.paused


class Pellet(object):
    def __init__(self, row, column):
        self.name = PELLET
        self.position = vec(column * twidth, row * theight)
        self.color = (255, 255, 255)
        self.rad = int(2 * twidth / 16)
        self.colrad = 2 * twidth / 16
        self.points = 10
        self.visible = True

    def render(self, screen):
        if self.visible:
            adjust = vec(twidth, theight) / 2
            p = self.position + adjust
            pygame.draw.circle(screen, self.color, p.asInt(), self.rad)


class PowerPellet(Pellet):
    def __init__(self, row, column):
        Pellet.__init__(self, row, column)
        self.name = POWERPELLET
        self.rad = int(8 * twidth / 16)
        self.points = 50
        self.ftime = 0.2
        self.timer = 0

    def update(self, dt):
        self.timer += dt
        if self.timer >= self.ftime:
            self.visible = not self.visible
            self.timer = 0


class Spritesheet(object):
    def __init__(self):
        self.sheet = pygame.image.load('sprites/spritesheet.png').convert()
        col = self.sheet.get_at((0, 0))
        self.sheet.set_colorkey(col)
        width = int(self.sheet.get_width() / BASETILEWIDTH * twidth)
        height = int(self.sheet.get_height() / BASETILEHEIGHT * theight)
        self.sheet = pygame.transform.scale(self.sheet, (width, height))

    def getImage(self, x, y, width, height):
        self.sheet.set_clip(pygame.Rect(x * twidth, y * theight, width, height))
        return self.sheet.subsurface(self.sheet.get_clip())


class PacmanSprites(Spritesheet):
    def __init__(self, entity):
        Spritesheet.__init__(self)
        self.entity = entity
        self.entity.image = self.getStartImage()
        self.animations = {}
        self.defineAnimations()
        self.stopimage = (8, 0)

    def defineAnimations(self):
        self.animations[left] = Animator(((8, 0), (0, 0), (0, 2), (0, 0)))
        self.animations[right] = Animator(((10, 0), (2, 0), (2, 2), (2, 0)))
        self.animations[up] = Animator(((10, 2), (6, 0), (6, 2), (6, 0)))
        self.animations[down] = Animator(((8, 2), (4, 0), (4, 2), (4, 0)))
        self.animations[DEATH] = Animator(((0, 12), (2, 12), (4, 12), (6, 12), (8, 12), (
            10, 12), (12, 12), (14, 12), (16, 12), (18, 12), (20, 12)), speed=6, loop=False)

    def update(self, dt):
        if self.entity.alive == True:
            if self.entity.direction == left:
                self.entity.image = self.getImage(*self.animations[left].update(dt))
                self.stopimage = (8, 0)
            elif self.entity.direction == right:
                self.entity.image = self.getImage(*self.animations[right].update(dt))
                self.stopimage = (10, 0)
            elif self.entity.direction == down:
                self.entity.image = self.getImage(*self.animations[down].update(dt))
                self.stopimage = (8, 2)
            elif self.entity.direction == up:
                self.entity.image = self.getImage(*self.animations[up].update(dt))
                self.stopimage = (10, 2)
            elif self.entity.direction == stop:
                self.entity.image = self.getImage(*self.stopimage)
        else:
            self.entity.image = self.getImage(*self.animations[DEATH].update(dt))

    def reset(self):
        [self.animations[key].reset() for key in list(self.animations.keys())]

    def getStartImage(self):
        return self.getImage(8, 0)

    def getImage(self, x, y):
        return Spritesheet.getImage(self, x, y, 2 * twidth, 2 * theight)


class GhostSprites(Spritesheet):
    def __init__(self, entity):
        Spritesheet.__init__(self)
        self.x = {bli: 0, pin: 2, ink: 4, cly: 6}
        self.entity = entity
        self.entity.image = self.getStartImage()

    def update(self, dt):
        x = self.x[self.entity.name]
        if self.entity.mode.cur in [SCATTER, CHASE]:
            if self.entity.direction == left:
                self.entity.image = self.getImage(x, 8)
            elif self.entity.direction == right:
                self.entity.image = self.getImage(x, 10)
            elif self.entity.direction == down:
                self.entity.image = self.getImage(x, 6)
            elif self.entity.direction == up:
                self.entity.image = self.getImage(x, 4)
        elif self.entity.mode.cur == FREIGHT:
            self.entity.image = self.getImage(10, 4)
        elif self.entity.mode.cur == SPAWN:
            if self.entity.direction == left:
                self.entity.image = self.getImage(8, 8)
            elif self.entity.direction == right:
                self.entity.image = self.getImage(8, 10)
            elif self.entity.direction == down:
                self.entity.image = self.getImage(8, 6)
            elif self.entity.direction == up:
                self.entity.image = self.getImage(8, 4)

    def getStartImage(self):
        return self.getImage(self.x[self.entity.name], 4)

    def getImage(self, x, y):
        return Spritesheet.getImage(self, x, y, 2 * twidth, 2 * theight)


class FruitSprites(Spritesheet):
    def __init__(self, entity, level):
        Spritesheet.__init__(self)
        self.entity = entity
        self.fruits = {0: (16, 8), 1: (18, 8), 2: (20, 8), 3: (16, 10), 4: (18, 10), 5: (20, 10)}
        self.entity.image = self.getStartImage(level % len(self.fruits))

    def getStartImage(self, key):
        return self.getImage(*self.fruits[key])

    def getImage(self, x, y):
        return Spritesheet.getImage(self, x, y, 2 * twidth, 2 * theight)


class LifeSprites(Spritesheet):
    def __init__(self, numlives):
        Spritesheet.__init__(self)
        self.resetLives(numlives)

    def removeImage(self):
        if len(self.images) > 0:
            self.images.pop(0)

    def resetLives(self, numlives):
        self.images = [self.getImage(0, 0) for i in range(numlives)]

    def getImage(self, x, y):
        return Spritesheet.getImage(self, x, y, 2 * twidth, 2 * theight)


class Text(object):
    def __init__(self, text, color, x, y, size, time=None, id=None, visible=True):
        self.id = id
        self.text = text
        self.color = color
        self.size = size
        self.visible = visible
        self.position = vec(x, y)
        self.timer = 0
        self.lifespan = time
        self.label = None
        self.destroy = False
        self.setupFont('fonts/PressStart2P-Regular.ttf')
        self.createLabel()

    def setupFont(self, fontpath):
        self.font = pygame.font.Font(fontpath, self.size)

    def createLabel(self):
        self.label = self.font.render(self.text, 1, self.color)

    def setText(self, newtext):
        self.text = str(newtext)
        self.createLabel()

    def update(self, dt):
        if self.lifespan is not None:
            self.timer += dt
            if self.timer >= self.lifespan:
                self.timer = 0
                self.lifespan = None
                self.destroy = True

    def render(self, screen):
        if self.visible:
            x, y = self.position.asTuple()
            screen.blit(self.label, (x, y))


class TextGroup(object):
    def __init__(self):
        self.nextid = 10
        self.alltext = {}
        self.setupText()
        self.showText(READYTXT)

    def addText(self, text, color, x, y, size, time=None, id=None):
        self.nextid += 1
        self.alltext[self.nextid] = Text(text, color, x, y, size, time=time, id=id)
        return self.nextid

    def removeText(self, id):
        self.alltext.pop(id)

    def setupText(self):
        size = theight
        self.alltext[SCORETXT] = Text('0'.zfill(8), (255, 255, 255), 0, theight, size)
        self.alltext[LEVELTXT] = Text(str(1).zfill(3), (255, 255, 255), 23 * twidth, theight, size)
        self.alltext[READYTXT] = Text('READY!', (255, 255, 0), 11.25 * twidth, 20 * theight, size, visible=False)
        self.alltext[PAUSETXT] = Text('PAUSED!', (255, 255, 0), 10.625 * twidth, 20 * theight, size, visible=False)
        self.alltext[GAMEOVERTXT] = Text('GAMEOVER!', (255, 255, 0), 10 * twidth, 20 * theight, size, visible=False)
        self.addText('SCORE', (255, 255, 255), 0, 0, size)
        self.addText('LEVEL', (255, 255, 255), 23 * twidth, 0, size)

    def update(self, dt):
        for tkey in list(self.alltext.keys()):
            self.alltext[tkey].update(dt)
            if self.alltext[tkey].destroy:
                self.removeText(tkey)

    def showText(self, id):
        self.hideText()
        self.alltext[id].visible = True

    def hideText(self):
        self.alltext[READYTXT].visible = False
        self.alltext[PAUSETXT].visible = False
        self.alltext[GAMEOVERTXT].visible = False

    def newScore(self, score):
        self.updateText(SCORETXT, str(score).zfill(8))

    def updateLevel(self, level):
        self.updateText(LEVELTXT, str(level + 1).zfill(3))

    def updateText(self, id, value):
        if id in self.alltext.keys():
            self.alltext[id].setText(value)

    def render(self, screen):
        [self.alltext[tkey].render(screen) for tkey in list(self.alltext.keys())]


class vec(object):
    def __init__(self, x=0, y=0):
        self.x, self.y = x, y

    def __add__(self, other):
        return vec(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return vec(self.x - other.x, self.y - other.y)

    def __neg__(self):
        return vec(-self.x, -self.y)

    def __mul__(self, scalar):
        return vec(self.x * scalar, self.y * scalar)

    def __div__(self, scalar):
        if scalar != 0:
            return vec(self.x / float(scalar), self.y / float(scalar))
        return

    def __truediv__(self, scalar):
        return self.__div__(scalar)

    def __eq__(self, other):
        return abs(self.x - other.x) < 0.000001 and abs(self.y - other.y) < 0.000001

    def magnitudeSquared(self):
        return self.x ** 2 + self.y ** 2

    def magnitude(self):
        return math.sqrt(self.magnitudeSquared())

    def copy(self):
        return vec(self.x, self.y)

    def asTuple(self):
        return self.x, self.y

    def asInt(self):
        return int(self.x), int(self.y)

    def __str__(self):
        return '<' + str(self.x) + ', ' + str(self.y) + '>'


class MazeSprites(Spritesheet):
    def __init__(self, mazefile, rotfile):
        Spritesheet.__init__(self)
        self.data = self.readmz(mazefile)
        self.rotdata = self.readmz(rotfile)

    def getImage(self, x, y):
        return Spritesheet.getImage(self, x, y, twidth, theight)

    def readmz(self, mazefile):
        return np.loadtxt(mazefile, dtype='<U1')

    def consBG(self, bg, y):
        for i in list(range(self.data.shape[0])):
            for j in list(range(self.data.shape[1])):
                if self.data[i][j].isdigit():
                    x = int(self.data[i][j]) + 12
                    sprite = self.getImage(x, y)
                    rotval = int(self.rotdata[i][j])
                    sprite = self.rotate(sprite, rotval)
                    bg.blit(sprite, (j * twidth, i * theight))
                elif self.data[i][j] == '=':
                    sprite = self.getImage(10, 8)
                    bg.blit(sprite, (j * twidth, i * theight))
        return bg

    def rotate(self, sprite, value):
        return pygame.transform.rotate(sprite, value * 90)


class PelletGroup(object):
    def __init__(self, pelletfile):
        self.pellist = []
        self.ppells = []
        self.createpel(pelletfile)
        self.cnt = 0

    def update(self, dt):
        [powerpellet.update(dt) for powerpellet in self.ppells]

    def createpel(self, pelletfile):
        data = self.readpel(pelletfile)
        for i in range(data.shape[0]):
            for j in range(data.shape[1]):
                if data[i][j] in ['.', '+']:
                    self.pellist.append(Pellet(i, j))
                elif data[i][j] in ['P', 'p']:
                    pp = PowerPellet(i, j)
                    self.pellist.append(pp)
                    self.ppells.append(pp)

    def readpel(self, textfile):
        return np.loadtxt(textfile, dtype='<U1')

    def isEmpty(self):
        return len(self.pellist) == 0

    def render(self, screen):
        [pellet.render(screen) for pellet in self.pellist]


class GameController(object):
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode(SCREENSIZE, 0, 32)
        self.bg = None
        self.bgn = None
        self.bgf = None
        self.clock = pygame.time.Clock()
        self.fruit = None
        self.pause = Pause(True)
        self.level = 0
        self.lives = 5
        self.score = 0
        self.TG = TextGroup()
        self.lifesprites = LifeSprites(self.lives)
        self.flashBG = False
        self.ftime = 0.2
        self.ftimer = 0
        self.fruitsc = []
        self.fruitNode = None
        self.mzdata = MazeData()

    def setBG(self):
        self.bgn = pygame.surface.Surface(SCREENSIZE).convert()
        self.bgn.fill((0, 0, 0))
        self.bgf = pygame.surface.Surface(SCREENSIZE).convert()
        self.bgf.fill((0, 0, 0))
        self.bgn = self.mazesprites.consBG(self.bgn, self.level % 5)
        self.bgf = self.mazesprites.consBG(self.bgf, 5)
        self.flashBG = False
        self.bg = self.bgn

    def start(self):
        self.mzdata.loadMaze(self.level)
        self.mazesprites = MazeSprites('levels/' + self.mzdata.obj.name + '.txt', 'levels/' + self.mzdata.obj.name + '_rotation.txt')
        self.setBG()
        self.nodes = NodeG('levels/' + self.mzdata.obj.name + '.txt')
        self.mzdata.obj.setPortalPairs(self.nodes)
        self.mzdata.obj.conHomnod(self.nodes)
        self.pacman = Pacman(self.nodes.getNodeFromTiles(*self.mzdata.obj.pacmanStart))
        self.pellets = PelletGroup('levels/' + self.mzdata.obj.name + '.txt')
        self.ghosts = GhostGroup(self.nodes.getStartTempNode(), self.pacman)
        self.ghosts.pinky.setStartNode(self.nodes.getNodeFromTiles(*self.mzdata.obj.addOffset(2, 3)))
        self.ghosts.inky.setStartNode(self.nodes.getNodeFromTiles(*self.mzdata.obj.addOffset(0, 3)))
        self.ghosts.clyde.setStartNode(self.nodes.getNodeFromTiles(*self.mzdata.obj.addOffset(4, 3)))
        self.ghosts.setSpawnNode(self.nodes.getNodeFromTiles(*self.mzdata.obj.addOffset(2, 3)))
        self.ghosts.blinky.setStartNode(self.nodes.getNodeFromTiles(*self.mzdata.obj.addOffset(2, 0)))
        self.nodes.denyHomeAccess(self.pacman)
        self.nodes.denyHomeAccessList(self.ghosts)
        self.ghosts.inky.startNode.denyAccess(right, self.ghosts.inky)
        self.ghosts.clyde.startNode.denyAccess(left, self.ghosts.clyde)
        self.mzdata.obj.GhostsA(self.ghosts, self.nodes)

    def starto(self):
        self.mzdata.loadMaze(self.level)
        self.mazesprites = MazeSprites('levels/maze1.txt', 'levels/maze1_rotation.txt')
        self.setBG()
        self.nodes = NodeG('levels/maze1.txt')
        self.nodes.setPortalPair((0, 17), (27, 17))
        homekey = self.nodes.createHomeNodes(11.5, 14)
        self.nodes.conHomnod(homekey, (12, 14), left)
        self.nodes.conHomnod(homekey, (15, 14), right)
        self.pacman = Pacman(self.nodes.getNodeFromTiles(15, 26))
        self.pellets = PelletGroup('levels/maze1.txt')
        self.ghosts = GhostGroup(self.nodes.getStartTempNode(), self.pacman)
        self.ghosts.blinky.setStartNode(self.nodes.getNodeFromTiles(2 + 11.5, 0 + 14))
        self.ghosts.pinky.setStartNode(self.nodes.getNodeFromTiles(2 + 11.5, 3 + 14))
        self.ghosts.inky.setStartNode(self.nodes.getNodeFromTiles(0 + 11.5, 3 + 14))
        self.ghosts.clyde.setStartNode(self.nodes.getNodeFromTiles(4 + 11.5, 3 + 14))
        self.ghosts.setSpawnNode(self.nodes.getNodeFromTiles(2 + 11.5, 3 + 14))
        self.nodes.denyHomeAccess(self.pacman)
        self.nodes.denyHomeAccessList(self.ghosts)
        self.nodes.denyAccessList(2 + 11.5, 3 + 14, left, self.ghosts)
        self.nodes.denyAccessList(2 + 11.5, 3 + 14, right, self.ghosts)
        self.ghosts.inky.startNode.denyAccess(right, self.ghosts.inky)
        self.ghosts.clyde.startNode.denyAccess(left, self.ghosts.clyde)
        self.nodes.denyAccessList(12, 14, up, self.ghosts)
        self.nodes.denyAccessList(15, 14, up, self.ghosts)
        self.nodes.denyAccessList(12, 26, up, self.ghosts)
        self.nodes.denyAccessList(15, 26, up, self.ghosts)

    def update(self):
        dt = self.clock.tick(30) / 1000.0
        self.TG.update(dt)
        self.pellets.update(dt)
        if not self.pause.paused:
            self.ghosts.update(dt)
            if self.fruit is not None:
                self.fruit.update(dt)
            self.PellE()
            self.ghostE()
            self.fruitE()
        if self.pacman.alive:
            if not self.pause.paused:
                self.pacman.update(dt)
        else:
            self.pacman.update(dt)
        if self.flashBG:
            self.ftimer += dt
            if self.ftimer >= self.ftime:
                self.ftimer = 0
                if self.bg == self.bgn:
                    self.bg = self.bgf
                else:
                    self.bg = self.bgn
        afterPauseMethod = self.pause.update(dt)
        if afterPauseMethod is not None:
            afterPauseMethod()
        self.checkEv()
        self.render()

    def checkEv(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    if self.pacman.alive:
                        self.pause.setPause(playerPaused=True)
                        if not self.pause.paused:
                            self.TG.hideText()
                            self.showEntities()
                        else:
                            self.TG.showText(PAUSETXT)

    def PellE(self):
        pellet = self.pacman.eatPellets(self.pellets.pellist)
        if pellet:
            self.pellets.cnt += 1
            self.newScore(pellet.points)
            if self.pellets.cnt == 30:
                self.ghosts.inky.startNode.allowAccess(right, self.ghosts.inky)
            if self.pellets.cnt == 70:
                self.ghosts.clyde.startNode.allowAccess(left, self.ghosts.clyde)
            self.pellets.pellist.remove(pellet)
            if pellet.name == POWERPELLET:
                self.ghosts.startFreight()
            if self.pellets.isEmpty():
                self.flashBG = True
                self.hideEntities()
                self.pause.setPause(pauseTime=3, func=self.next)

    def ghostE(self):
        for ghost in self.ghosts:
            if self.pacman.collideGhost(ghost):
                if ghost.mode.cur is FREIGHT:
                    self.pacman.visible = False
                    ghost.visible = False
                    self.newScore(ghost.points)
                    self.TG.addText(str(ghost.points), (255, 255, 255), ghost.position.x, ghost.position.y, 8, time=1)
                    self.ghosts.updatePoints()
                    self.pause.setPause(pauseTime=1, func=self.showEntities)
                    ghost.startSpawn()
                    self.nodes.allowHomeAccess(ghost)
                elif ghost.mode.cur is not SPAWN:
                    if self.pacman.alive:
                        self.lives -= 1
                        self.lifesprites.removeImage()
                        self.pacman.die()
                        self.ghosts.hide()
                        if self.lives <= 0:
                            self.TG.showText(GAMEOVERTXT)
                            self.pause.setPause(pauseTime=3, func=self.restart)
                        else:
                            self.pause.setPause(pauseTime=3, func=self.reset)

    def fruitE(self):
        if self.pellets.cnt == 50 or self.pellets.cnt == 140:
            if self.fruit is None:
                self.fruit = Fruit(self.nodes.getNodeFromTiles(9, 20), self.level)
                print(self.fruit)
        if self.fruit is not None:
            if self.pacman.collideCheck(self.fruit):
                self.newScore(self.fruit.points)
                self.TG.addText(str(self.fruit.points), (255, 255, 255), self.fruit.position.x, self.fruit.position.y, 8,
                                       time=1)
                fruitsc = False
                for fruit in self.fruitsc:
                    if fruit.get_offset() == self.fruit.image.get_offset():
                        fruitsc = True
                        break
                if not fruitsc:
                    self.fruitsc.append(self.fruit.image)
                self.fruit = None
            elif self.fruit.destroy:
                self.fruit = None

    def showEntities(self):
        self.pacman.visible = True
        self.ghosts.show()

    def hideEntities(self):
        self.pacman.visible = False
        self.ghosts.hide()

    def next(self):
        self.showEntities()
        self.level += 1
        self.pause.paused = True
        self.start()
        self.TG.updateLevel(self.level)

    def restart(self):
        self.lives = 5
        self.level = 0
        self.pause.paused = True
        self.fruit = None
        self.start()
        self.score = 0
        self.TG.newScore(self.score)
        self.TG.updateLevel(self.level)
        self.TG.showText(READYTXT)
        self.lifesprites.resetLives(self.lives)
        self.fruitsc = []

    def reset(self):
        self.pause.paused = True
        self.pacman.reset()
        self.ghosts.reset()
        self.fruit = None
        self.TG.showText(READYTXT)

    def newScore(self, points):
        self.score += points
        self.TG.newScore(self.score)

    def render(self):
        self.screen.blit(self.bg, (0, 0))
        self.pellets.render(self.screen)
        if self.fruit is not None:
            self.fruit.render(self.screen)
        self.pacman.render(self.screen)
        self.ghosts.render(self.screen)
        self.TG.render(self.screen)
        for i in range(len(self.lifesprites.images)):
            x = self.lifesprites.images[i].get_width() * i
            y = screenh - self.lifesprites.images[i].get_height()
            self.screen.blit(self.lifesprites.images[i], (x, y))
        for i in range(len(self.fruitsc)):
            x = screenw - self.fruitsc[i].get_width() * (i + 1)
            y = screenh - self.fruitsc[i].get_height()
            self.screen.blit(self.fruitsc[i], (x, y))
        pygame.display.update()


if __name__ == '__main__':
    game = GameController()
    game.start()
    while True:
        game.update()