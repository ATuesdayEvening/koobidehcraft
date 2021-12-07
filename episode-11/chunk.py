import ctypes

import pyglet.gl as gl

import subchunk 

CHUNK_WIDTH = 16
CHUNK_HEIGHT = 128
CHUNK_LENGTH = 16

class Chunk:
	def __init__(self, world, chunk_position):
		self.world = world
		
		self.modified = False
		self.chunk_position = chunk_position

		self.position = (
			self.chunk_position[0] * CHUNK_WIDTH,
			self.chunk_position[1] * CHUNK_HEIGHT,
			self.chunk_position[2] * CHUNK_LENGTH)
		
		self.blocks = [[[0
			for z in range(CHUNK_LENGTH)]
			for y in range(CHUNK_HEIGHT)]
			for x in range(CHUNK_WIDTH )]

		self.subchunks = {}
		
		for x in range(int(CHUNK_WIDTH / subchunk.SUBCHUNK_WIDTH)):
			for y in range(int(CHUNK_HEIGHT / subchunk.SUBCHUNK_HEIGHT)):
				for z in range(int(CHUNK_LENGTH / subchunk.SUBCHUNK_LENGTH)):
					self.subchunks[(x, y, z)] = subchunk.Subchunk(self, (x, y, z))

		# mesh variables

		self.mesh = []
		self.translucent_mesh = []

		self.mesh_quad_count = 0
		self.translucent_quad_count = 0

		# create VAO and VBO's

		self.vao = gl.GLuint(0)
		gl.glGenVertexArrays(1, ctypes.byref(self.vao))
		gl.glBindVertexArray(self.vao)

		self.vbo = gl.GLuint(0)
		gl.glGenBuffers(1, ctypes.byref(self.vbo))
		gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbo)

		gl.glVertexAttribPointer(0, 3, gl.GL_FLOAT, 
				gl.GL_FALSE, 7 * ctypes.sizeof(gl.GLfloat), 0)
		gl.glEnableVertexAttribArray(0)
		gl.glVertexAttribPointer(1, 3, gl.GL_FLOAT, 
				gl.GL_FALSE, 7 * ctypes.sizeof(gl.GLfloat), 3 * ctypes.sizeof(gl.GLfloat))
		gl.glEnableVertexAttribArray(1)
		gl.glVertexAttribPointer(2, 1, gl.GL_FLOAT, 
				gl.GL_FALSE, 7 * ctypes.sizeof(gl.GLfloat), 6 * ctypes.sizeof(gl.GLfloat))
		gl.glEnableVertexAttribArray(2)

		gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, world.ibo)

	def __del__(self):
		gl.glDeleteBuffers(1, ctypes.byref(self.vbo))
		gl.glDeleteVertexArrays(1, ctypes.byref(self.vao))
	
	def update_subchunk_meshes(self):
		for subchunk_position in self.subchunks:
			subchunk = self.subchunks[subchunk_position]
			subchunk.update_mesh()

	def update_at_position(self, position):
		x, y, z = position

		lx = int(x % subchunk.SUBCHUNK_WIDTH )
		ly = int(y % subchunk.SUBCHUNK_HEIGHT)
		lz = int(z % subchunk.SUBCHUNK_LENGTH)

		clx, cly, clz = self.world.get_local_position(position)

		sx = clx // subchunk.SUBCHUNK_WIDTH
		sy = cly // subchunk.SUBCHUNK_HEIGHT
		sz = clz // subchunk.SUBCHUNK_LENGTH

		self.subchunks[(sx, sy, sz)].update_mesh()

		def try_update_subchunk_mesh(subchunk_position):
			if subchunk_position in self.subchunks:
				self.subchunks[subchunk_position].update_mesh()

		if lx == subchunk.SUBCHUNK_WIDTH - 1: try_update_subchunk_mesh((sx + 1, sy, sz))
		if lx == 0: try_update_subchunk_mesh((sx - 1, sy, sz))

		if ly == subchunk.SUBCHUNK_HEIGHT - 1: try_update_subchunk_mesh((sx, sy + 1, sz))
		if ly == 0: try_update_subchunk_mesh((sx, sy - 1, sz))

		if lz == subchunk.SUBCHUNK_LENGTH - 1: try_update_subchunk_mesh((sx, sy, sz + 1))
		if lz == 0: try_update_subchunk_mesh((sx, sy, sz - 1))

	def update_mesh(self):
		# combine all the small subchunk meshes into one big chunk mesh

		for subchunk_position in self.subchunks:
			subchunk = self.subchunks[subchunk_position]

			self.mesh.extend(subchunk.mesh)
			self.translucent_mesh.extend(subchunk.translucent_mesh)
		
		# send the full mesh data to the GPU and free the memory used client-side (we don't need it anymore)
		# don't forget to save the length of 'self.mesh_indices' before freeing

		self.mesh_quad_count = len(self.mesh) // 28
		self.translucent_quad_count = len(self.translucent_mesh) // 28

		self.send_mesh_data_to_gpu()
	
		self.mesh = []
		self.translucent_mesh = []
	
	def send_mesh_data_to_gpu(self): # pass mesh data to gpu
		if not self.mesh_quad_count:
			return

		self.mesh.extend(self.translucent_mesh)

		gl.glBindVertexArray(self.vao)

		gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbo)
		gl.glBufferData(
			gl.GL_ARRAY_BUFFER,
			ctypes.sizeof(gl.GLfloat * len(self.mesh)),
			(gl.GLfloat * len(self.mesh)) (*self.mesh),
			gl.GL_DYNAMIC_DRAW)


	def draw(self):
		if not self.mesh_quad_count:
			return
		
		gl.glBindVertexArray(self.vao)

		gl.glDrawElementsBaseVertex(
			gl.GL_TRIANGLES,
			self.mesh_quad_count * 6,
			gl.GL_UNSIGNED_INT,
			None,
			0)

	def draw_translucent(self):
		if not self.translucent_quad_count:
			return
		
		gl.glBindVertexArray(self.vao)

		gl.glDrawElementsBaseVertex(
			gl.GL_TRIANGLES,
			self.translucent_quad_count * 6,
			gl.GL_UNSIGNED_INT,
			None,
			self.mesh_quad_count * 4
		)