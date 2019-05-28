'''
Реализация стратегии для чемпионата RussianAI Cup 2018.
Требовалось реализовать алгоритм, которым руководствовались бы роботы, играя в футбол.
Подробнее здесь https://russianaicup.ru/p/about
Данная стратегия заняла 263/670 место.

В целом надо было отдельно прописать стратегии для вратаря и полевого игрока. Полевой игрок
частенько делал нехорошие движения. Например, при заходе на удар, он часто колебался с углом атаки.
Также при расчете, под каким углом забегать, он не учитывает существующий импульс мяча. То есть
мяч считается неподвижным. Однако в ряде случаев он все равно бил точно по воротам.
Вратарь же получился довольно хорошим. Почти все дальние удары он отбивал без проблем. Если мяч
летел по воздуху, вратарь в какой-то рассчитанный момент начинал выбегать, а в нужный момент подпрыгивать. Этим он сильно выбивал мяч в сторону противника. Удары "низом" также не составляли для него труда. Голы пропускались в основном по двум причинам. Либо в последний момент кто-то из игроков подправлял мяч, изменяя его траекторию (точка встречи резко менялась, а вратарь уже не успевал перестроиться). Либо возникала борьба около ворот и вратарь уже не мог набрать нужного разбега, чтобы выбить мяч подальше.
'''
# Необходимые включения
from model.action import Action
from model.game import Game
from model.robot import Robot
from model.rules import Rules
from math import cos
import time

# Константы, взятые из документации
EPS = 1e-5
BALL_RADIUS = 2.0
ROBOT_MAX_RADIUS = 1.05
MAX_ENTITY_SPEED = 100.0
ROBOT_MAX_GROUND_SPEED = 30.0
ROBOT_MAX_JUMP_SPEED = 15.0
JUMP_TIME = 0.2
MAX_JUMP_HEIGHT = 3.0


class Vector2D:
    # Нам понадобится работа с 2d векторами
	def __init__(self, x=0.0, z=0.0):
		self.x = x
		self.z = z

    # Нахождение длины вектора
	def len(self):
		return ((self.x * self.x) + (self.z * self.z))**0.5

    # Операция - для векторов
	def __sub__(self, other):
		return Vector2D(self.x - other.x, self.z - other.z)

    # Операция + для векторов
	def __add__(self, other):
		return Vector2D(self.x + other.x, self.z + other.z)

    # Операция умножения вектора на число
	def __mul__(self, num: float):
		return Vector2D(self.x * num, self.z * num)

    # Нормализация вектора (приведение длины к 1)
	def normalize(self):
		return Vector2D(self.x/self.len(), self.z/self.len())
    
    # Косинус угла между объектом и другим вектором
	def cosine(self,vect):
		len1 = self.len()
		len2 = vect.len()
		chisl = self.x*vect.x+self.z+vect.z
		return chisl / (len1*len2)
    
    # Поворот вектора на угол angle вправо
	def right(self,angle):
		cosine = cos(angle)
		sinus = (1-cosine**2)**0.5
		temp = Vector2D(self.x,self.z)
		temp.x = self.x*cosine + sinus * self.z
		temp.z = -self.x*sinus + cosine * self.z
		return temp
    
    # Поворот вектора на угол angle влево
	def left(self,angle):
		cosine = cos(angle)
		sinus = (1-cosine**2)**0.5
		temp = Vector2D(self.x,self.z)
		temp.x = self.x*cosine - sinus * self.z
		temp.z = self.x*sinus + cosine * self.z
		return temp

# Косинус между двумя углами в виде функции
def cosine(a,b):
	len1 = a.len()
	len2 = b.len()
	chisl = a.x*b.x+a.z*b.z
	return (chisl / (len1*len2))

class MyStrategy:
    # Код стратегии
	
	def __init__(self):
		self.x = 0
		self.z = 0
    
	def act(self, me: Robot, rules: Rules, game: Game, action: Action):
		
        # Наша стратегия умеет играть только на земле
        # Поэтому, если мы не касаемся земли, будет использовать нитро
        # чтобы как можно быстрее попасть обратно на землю
		if not me.touch:
			action.target_velocity_x = 0.0
			action.target_velocity_y = -MAX_ENTITY_SPEED
			action.target_velocity_z = 0.0
			action.jump_speed = 0.0
			action.use_nitro = True
			return

        # Найдем расстояние между мячом и роботом
		dist_to_ball = ((me.x - game.ball.x) ** 2
                        + (me.y - game.ball.y) ** 2
                        + (me.z - game.ball.z) ** 2
                        ) ** 0.5
        
        # Найдем расстояние в плоскости xz (горизонтальной)
		dist_to_ball_xz = ((me.x-game.ball.x)**2 + (me.z-game.ball.z)**2)**0.5
        
        # Если при прыжке произойдет столкновение с мячом, и мы находимся
        # с той же стороны от мяча, что и наши ворота, прыгнем, тем самым
        # ударив по мячу сильнее в сторону противника
		jump = (dist_to_ball < BALL_RADIUS +ROBOT_MAX_RADIUS and me.z < game.ball.z)

        # Далее описываются действия нападающего, который может иметь id либо 2, либо 4
		if me.id==2 or me.id==4:

            # Если роботы вылетают за пределы горизонтального участка,
            # придаем скорость, которая вернет их назад 
			if me.z < -rules.arena.depth/2.0+rules.arena.bottom_radius:
				action.target_velocity_z = ROBOT_MAX_GROUND_SPEED
				return
			if me.x > rules.arena.width/2.0:
				action.target_velocity_x = -ROBOT_MAX_GROUND_SPEED
				return
			if me.x < -rules.arena.width/2.0:
				action.target_velocity_x = ROBOT_MAX_GROUND_SPEED
				return
			e = 0.001
            # Если мяч не вылетит за пределы арены
            # (произойдет столкновение со стеной, которое мы не рассматриваем),
            # и при этом мяч будет находится ближе к вражеским воротам, чем робот,
			if game.ball.z > me.z and abs(game.ball.x) < (rules.arena.width / 2.0) \
                        and abs(game.ball.z) < (rules.arena.depth / 2.0):

                # Посчитаем, с какой скоростью робот должен бежать,
                # Чтобы прийти туда же, где будет мяч, в то же самое время

				target_pos = Vector2D(0.0, (rules.arena.depth / 2.0) + rules.arena.bottom_radius)
				ball_pos = Vector2D(game.ball.x,game.ball.z)
				a = target_pos - ball_pos
				b = target_pos - Vector2D(me.x,me.z)
				c = ball_pos - Vector2D(me.x,me.z)
				cosine_a_b = cosine(a,b)
				cos_y = cosine(a,c)
				delta_pos = Vector2D(ball_pos.x, ball_pos.z) - Vector2D(me.x, me.z)
				
				# Если вектор скорости робота не сонаправлен с вектором, по которому требуется
                # ударить, чтобы мяч попал в центр ворот, то стремимся двигаться в сторону
                # увеличения cosine_a_b
				if abs(cosine_a_b) < 1 - e:
					
					#print(cos_y)	
					sin_y = (1-cos_y**2)**0.5
                        #print(cos_y,a.x,a.z,a.len(),c.x,c.z,c.len())
					if cos_y > 1:
						time.sleep(30)
                        
						assert(cos_y < 1)
					if c.x > 0:
						x_d = c.x*cos_y+sin_y*c.z
						z_d = -c.x*sin_y+cos_y*c.z
					else:
						x_d = c.x*cos_y-sin_y*c.z
						z_d = c.x*sin_y+cos_y*c.z
					d = Vector2D(x_d,z_d)
#                        print(d.x,d.z)
#					d.z = d.z if game.ball.y < 3 * BALL_RADIUS else -d.z
					target_velocity = d.normalize()*ROBOT_MAX_GROUND_SPEED
					
                # В противном случае бежим на мяч
				else:
					ball_pos = Vector2D(game.ball.x,game.ball.z)
					me_pos = Vector2D(me.x,me.z)
					delta_to_ball = ball_pos - me_pos
					target_velocity = delta_to_ball.normalize()*ROBOT_MAX_GROUND_SPEED 

                # Если мяч летит в воздухе, надо научиться прыгать ровно в место встречи
				if game.ball.y > 2 * BALL_RADIUS and dist_to_ball_xz < 2 * BALL_RADIUS:
                    # Для этого надо понять, через какое время мяч вернется на землю
					v0 = game.ball.velocity_y
					R = 2 * BALL_RADIUS
					h = game.ball.y
					g = 30
					D = 4 * v0 * v0 - 4 * g * (2 * R - 2 * h)
					t = v0 / g + (D**0.5) / (2 * g)
					
					ball_pos_z = game.ball.z + game.ball.velocity_z*t*60
					ball_pos_x = game.ball.x + game.ball.velocity_x*t*60
					ball_pos = Vector2D(ball_pos_x,ball_pos_z)

					delta_dist_z = ball_pos_z - me.z
					velocity_z = delta_dist_z / (0.5*t+0.01)
					delta_dist_x = ball_pos_x - me.x
					velocity_x = delta_dist_x / (0.5*t+0.01)

					target_velocity = Vector2D(velocity_x,velocity_z)			
                # Установим итоговую скорость
				action.target_velocity_x = target_velocity.x
				action.target_velocity_y = 0.0
				action.target_velocity_z = target_velocity.z
				action.jump_speed = ROBOT_MAX_JUMP_SPEED if jump  else 0.0
                
                # Теперь разберемся, нужно ли прыгать, если при текущих скоростях, шар и робот
                # встретятся  в воздухе
				ball_pos_x = game.ball.x
				ball_pos_y = game.ball.y
				ball_pos_z = game.ball.z
				speed_y_ball = game.ball.velocity_y
				delta_time = 2 / 60 / 100
				speed_y = ROBOT_MAX_JUMP_SPEED
				me_y = 1
				me_x = me.x
				me_z = me.z

                # Произведем небольшое моделирование ситуации
				for i in range(40*50):
					if game.ball.z < me.z:
						break
					ball_pos_x += game.ball.velocity_x*delta_time
					ball_pos_y += speed_y_ball*delta_time
					ball_pos_z += game.ball.velocity_z*delta_time
					ball_pos_y -= 15*delta_time*delta_time
					speed_y_ball -= 30*delta_time
					me_y += speed_y*delta_time
					me_y -= 15*delta_time*delta_time
					speed_y -= 30*delta_time 
					if ball_pos_y < 2:
						speed_y_ball -= (1.7)*speed_y_ball
					me_x += me.velocity_x*delta_time
					me_z += me.velocity_z*delta_time
					dist_ball = ((me_x - ball_pos_x) ** 2
            	           + (me_y - ball_pos_y) ** 2
               	        + (me_z - ball_pos_z) ** 2
               	        ) ** 0.5
					gen_velocity = (speed_y ** 2+ me.velocity_x ** 2 + me.velocity_z ** 2) **0.5
				
                    # Если робот и шар пересекаются
					if dist_ball < (0.5*BALL_RADIUS +ROBOT_MAX_RADIUS) and abs(me_y-ball_pos_y) < 1  and i < 7000 and\
					speed_y / gen_velocity < 0.5  and cos_y >0.81 or jump:
                        # Тогда надо прыгать прямо сейчас
                        # В полете робот неуправляем, поэтому решение о прыжке - довольно ответственно
                        
						action.jump_speed = ROBOT_MAX_JUMP_SPEED
						break
				if jump:
						action.jump_speed = ROBOT_MAX_JUMP_SPEED
					

				


				action.use_nitro = False
				return
            
            # Если ничего не реализовалось, просто бежим на стартовую позицию
			target_pos = Vector2D(0.0, -(rules.arena.depth / 2.0) + rules.arena.bottom_radius)
			target_velocity = Vector2D(
            target_pos.x - me.x, target_pos.z - me.z) * ROBOT_MAX_GROUND_SPEED
			action.target_velocity_x = target_velocity.x
			action.target_velocity_y = 0.0
			action.target_velocity_z = target_velocity.z
			return


        # Стратегия защитника:
        # Будем стоять посередине наших ворот

		radius = rules.arena.bottom_radius
		target_pos= Vector2D(0.0, -(rules.arena.depth / 2.0))
		target_velocity = Vector2D((target_pos.x - me.x), (target_pos.z - me.z))*\
                               ROBOT_MAX_GROUND_SPEED

		t = 1
		ball_pos_x = game.ball.x
		ball_pos_y = game.ball.y
		ball_pos_z = game.ball.z
		speed_y_ball = game.ball.velocity_y
		delta_time = 1 / 60 / 100
		speed_y = ROBOT_MAX_JUMP_SPEED
		me_y = 1
		me_x = me.x
		me_z = me.z

        # Произведем моделирование ситуации
		i = 0
		for i in range(70*100):
            # Чтобы не тратить драгоценное время, если шар на чужой половине поля
            # не будем моделировать. На практике это не приводит к пропущенным мячам
			if game.ball.z > 0:
				break
            
			ball_pos_x += game.ball.velocity_x*delta_time
			ball_pos_y += speed_y_ball*delta_time
			ball_pos_z += game.ball.velocity_z*delta_time
			ball_pos_y -= 15*delta_time*delta_time
			speed_y_ball -= 30*delta_time
			target_z = -(rules.arena.depth / 2.0) + rules.arena.bottom_radius
			me_y += speed_y * delta_time
			me_y -= 15 * delta_time*delta_time
			speed_y -= 30 * delta_time
			me_x += me.velocity_x*delta_time
			me_z += me.velocity_z*delta_time
			dist_ball = ((me_x - ball_pos_x)**2+(me_y-ball_pos_y)**2+
			(me_z-ball_pos_z)**2)**0.5

			gen_velocity = (speed_y ** 2+ me.velocity_x ** 2 + me.velocity_z ** 2) **0.5
			t = int(i/100)
			delta_dist_z = ball_pos_z - me.z
			velocity_z = delta_dist_z / (t+0.01)
			delta_dist_x = ball_pos_x - me.x
			velocity_x = delta_dist_x / (t+0.01)
			h = ball_pos_y - me_y
			# Если ожидаем столкновение с мячом в воздухе - прыгаем
			if dist_ball <(BALL_RADIUS+ROBOT_MAX_RADIUS) and (ball_pos_y > me_y):
				action.jump_speed = ROBOT_MAX_JUMP_SPEED
                
            # Если мяч должен прилететь в зону ворот, бежим на мяч
			if (ball_pos_z < -(rules.arena.depth / 2.0) + rules.arena.bottom_radius+10) and \
			(abs(ball_pos_x) < rules.arena.goal_width / 2.0) and ball_pos_y < 2*BALL_RADIUS and\
			me_z < ball_pos_z and h / dist_ball < 0.5:
			
				target_velocity = Vector2D(velocity_x,velocity_z)*60
				self.x = target_velocity.x
				self.z = target_velocity.z
				break				
        # Выставляем команды
		action.target_velocity_x = target_velocity.x
		action.target_velocity_y = 0
		action.target_velocity_z = target_velocity.z
		action.use_nitro = False
		if jump:
			action.jump_speed = ROBOT_MAX_JUMP_SPEED


	def custom_rendering(self):
		return  str(self.x)+'\n'+str(self.z)
