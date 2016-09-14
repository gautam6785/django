class DoublyLinkedListNode():
  def __init__(self, data, prev, next):
    self.data = data
    self.prev = prev
    self.next = next

class DoublyLinkedList(object):
  def __init__(self):
    self.head = None
    self.tail = None
    self.length = 0

  def __len__(self):
    return self.length

  def __iter__(self):
    return DoublyLinkedListIterator(self)

  def __str__(self):
    dataList = []
    node = self.head
    while node:
      dataList.append(node.data)
      node = node.next
    return str(dataList)

  def append(self, data):
    node = DoublyLinkedListNode(data, None, None)
    if self.tail is None:
      self.head = self.tail = node
    else:
      node.prev = self.tail
      self.tail.next = node
      self.tail = node
    self.length += 1

  def appendleft(self, data):
    node = DoublyLinkedListNode(data, None, None)
    if self.head is None:
      self.head = self.tail = node
    else:
      node.next = self.head
      self.head.prev = node
      self.head = node
    self.length += 1

  def pop(self):
    if self.tail is None:
      raise IndexError('pop from empty DoublyLinkedList')
    ret = self.tail.data
    self.tail = self.tail.prev
    self.length -= 1
    return ret

  def popleft(self):
    if self.head is None:
      raise IndexError('popleft from empty DoublyLinkedList')
    ret = self.head.data
    self.head = self.head.next
    self.length -= 1
    return ret

  def find(self, data_func, data_arg):
    if self.head is None:
      return None
    node = self.head
    while not data_func(data_arg, node.data):
      if node.next is None:
        return None
      node = node.next
    return node

  def findright(self, data_func, data_arg):
    if self.tail is None:
      return None
    node = self.tail
    while not data_func(data_arg, node.data):
      if node.prev is None:
        return None
      node = node.prev
    return node

  def insertleft(self, data, node):
    if node is None:
      raise ValueError('node value of None passed to insertleft')
    new_node = DoublyLinkedListNode(data, None, node)
    new_node.prev = node.prev
    if node.prev is not None:
      node.prev.next = new_node
    node.prev = new_node
    if self.head == node:
      self.head = new_node
    self.length += 1

  def insertright(self, data, node):
    if node is None:
      raise ValueError('node value of None passed to insertright')
    new_node = DoublyLinkedListNode(data, node, None)
    new_node.next = node.next
    if node.next is not None:
      node.next.prev = new_node
    node.next = new_node
    if self.tail == node:
      self.tail = new_node
    self.length += 1

  def delete(self, node):
    if node is None:
      raise ValueError('node value of None passed to delete')
    if node.prev is not None:
      node.prev.next = node.next
    if node.next is not None:
      node.next.prev = node.prev
    if self.head == node:
      self.head = node.next
    if self.tail == node:
      self.tail = node.prev
    self.length -= 1

class DoublyLinkedListIterator(object):
  def __init__(self, doubly_linked_list):
    self.current_node = doubly_linked_list.head

  def __iter__(self):
    return self

  def next(self):
    if self.current_node is None:
      raise StopIteration
    ret = self.current_node.data
    self.current_node = self.current_node.next
    return ret
